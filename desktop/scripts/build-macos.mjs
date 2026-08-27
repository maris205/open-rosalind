import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

import {
  isFormalRelease,
  tauriArguments,
  validateFormalReleaseEnvironment
} from "./macos-release-policy.mjs";

if (process.platform !== "darwin") {
  throw new Error("The macOS bundle command must run on macOS.");
}

const desktopRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const tauri = path.join(desktopRoot, "node_modules", ".bin", "tauri");
const environment = { ...process.env };
const requestedArguments = process.argv.slice(2);
const formalRelease = isFormalRelease(requestedArguments, environment);
const buildArguments = tauriArguments(requestedArguments);

if (formalRelease) validateFormalReleaseEnvironment(environment);

if (environment.APPLE_CERTIFICATE && !environment.APPLE_SIGNING_IDENTITY) {
  throw new Error(
    "Embedded Python signing requires APPLE_SIGNING_IDENTITY to reference an identity already installed in the build keychain."
  );
}

// Local alpha packages still need a complete bundle signature so that both the
// .app and the copy embedded in the .dmg pass codesign verification. Preserve
// real Developer ID/CI credentials whenever they are configured.
if (!environment.APPLE_SIGNING_IDENTITY && !environment.APPLE_CERTIFICATE) {
  environment.APPLE_SIGNING_IDENTITY = "-";
}

const run = (command, args, options = {}) => {
  const commandResult = spawnSync(command, args, { stdio: "inherit", ...options });
  if (commandResult.error) throw commandResult.error;
  if (commandResult.status !== 0) {
    throw new Error(`${command} exited with status ${commandResult.status}`);
  }
};

const capture = (command, args, options = {}) => {
  const commandResult = spawnSync(command, args, { encoding: "utf8", ...options });
  if (commandResult.error) throw commandResult.error;
  if (commandResult.status !== 0) {
    throw new Error(`${command} exited with status ${commandResult.status}`);
  }
  return `${commandResult.stdout || ""}${commandResult.stderr || ""}`;
};

const targetIndex = buildArguments.indexOf("--target");
const targetName = targetIndex >= 0 ? buildArguments[targetIndex + 1] : "";
const expectedRuntimeArchitectures = targetName.includes("universal")
  ? ["arm64", "x64"]
  : targetName.includes("x86_64")
    ? ["x64"]
    : targetName.includes("aarch64")
      ? ["arm64"]
      : [process.arch];
const releaseRoot = targetName
  ? path.join(desktopRoot, "src-tauri", "target", targetName, "release")
  : path.join(desktopRoot, "src-tauri", "target", "release");
const bundleRoot = path.join(releaseRoot, "bundle");
const appDirectory = path.join(bundleRoot, "macos");
const dmgDirectory = path.join(bundleRoot, "dmg");

function findPythonBytecode(directory, matches = []) {
  for (const entry of fs.readdirSync(directory, { withFileTypes: true })) {
    const entryPath = path.join(directory, entry.name);
    if (entry.isDirectory()) {
      if (entry.name === "__pycache__") matches.push(entryPath);
      else findPythonBytecode(entryPath, matches);
    } else if (entry.isFile() && entry.name.endsWith(".pyc")) {
      matches.push(entryPath);
    }
  }
  return matches;
}

function findMachOBinaries(directory, matches = []) {
  for (const entry of fs.readdirSync(directory, { withFileTypes: true })) {
    const entryPath = path.join(directory, entry.name);
    if (entry.isDirectory()) {
      findMachOBinaries(entryPath, matches);
    } else if (entry.isFile()) {
      const mode = fs.statSync(entryPath).mode;
      const likelyNativeCode = entry.name.includes(".so")
        || entry.name.endsWith(".dylib")
        || (mode & 0o111) !== 0;
      if (!likelyNativeCode) continue;
      const description = capture("file", ["-b", entryPath]);
      if (description.includes("Mach-O")) matches.push(entryPath);
    }
  }
  return matches;
}

function verifyDeveloperIdSignature(target) {
  const details = capture("codesign", ["--display", "--verbose=4", target]);
  if (!details.includes("Authority=Developer ID Application:")) {
    throw new Error(`Formal release target does not have a Developer ID Application signature: ${target}`);
  }
}

function signEmbeddedPythonRuntime() {
  const identity = environment.APPLE_SIGNING_IDENTITY;
  for (const architecture of expectedRuntimeArchitectures) {
    const runtime = path.join(desktopRoot, "python-runtime", architecture);
    if (!fs.existsSync(runtime)) throw new Error(`Missing prepared Python runtime: ${runtime}`);
    const binaries = findMachOBinaries(runtime);
    if (!binaries.length) throw new Error(`No Mach-O files found in prepared Python runtime: ${runtime}`);
    for (const binary of binaries) {
      const argumentsList = ["--force", "--sign", identity];
      if (formalRelease) argumentsList.push("--timestamp", "--options", "runtime");
      argumentsList.push(binary);
      run("codesign", argumentsList);
      run("codesign", ["--verify", "--strict", "--verbose=2", binary]);
      if (formalRelease) verifyDeveloperIdSignature(binary);
    }
  }
}

signEmbeddedPythonRuntime();

const result = spawnSync(tauri, ["build", ...buildArguments], {
  cwd: desktopRoot,
  env: environment,
  stdio: "inherit"
});

if (result.error) throw result.error;
if (result.status !== 0) process.exit(result.status ?? 1);

const appBundles = fs.existsSync(appDirectory)
  ? fs.readdirSync(appDirectory).filter((name) => name.endsWith(".app")).map((name) => path.join(appDirectory, name))
  : [];

function verifyAppBundle(appBundle) {
  run("codesign", ["--verify", "--deep", "--strict", "--verbose=2", appBundle]);
  const runtimeRoot = path.join(appBundle, "Contents", "Resources", "runtime");
  const pythonRuntimeRoot = path.join(runtimeRoot, "python-runtime");
  const packagedArchitectures = fs.readdirSync(pythonRuntimeRoot, { withFileTypes: true })
    .filter((entry) => entry.isDirectory() && ["arm64", "x64"].includes(entry.name))
    .map((entry) => entry.name)
    .sort();
  if (packagedArchitectures.join(",") !== [...expectedRuntimeArchitectures].sort().join(",")) {
    throw new Error(`Unexpected embedded Python architectures in ${appBundle}: ${packagedArchitectures.join(", ")}`);
  }
  for (const architecture of expectedRuntimeArchitectures) {
    const python = path.join(pythonRuntimeRoot, architecture, "bin", "python3");
    if (!fs.existsSync(python)) throw new Error(`Missing embedded Python executable: ${python}`);
    run(python, [
      "-I", "-B", "-c",
      `import json, platform, pathlib, sys; import docx, lxml, pypdf, redis, rq, sqlalchemy; expected=${JSON.stringify(architecture === "arm64" ? "arm64" : "x86_64")}; assert platform.machine() == expected, (platform.machine(), expected); assert pathlib.Path(sys.executable).resolve().is_relative_to(pathlib.Path(${JSON.stringify(appBundle)}).resolve()); print(json.dumps({'python': platform.python_version(), 'machine': platform.machine()}))`
    ], { env: { ...environment, PYTHONDONTWRITEBYTECODE: "1", PYTHONNOUSERSITE: "1", PYTHONSAFEPATH: "1" } });
  }
  const bytecode = findPythonBytecode(runtimeRoot);
  if (bytecode.length) {
    throw new Error(`Python bytecode must not be packaged; found ${bytecode.slice(0, 5).join(", ")}`);
  }
  const nestedBinaries = findMachOBinaries(pythonRuntimeRoot);
  if (!nestedBinaries.length) throw new Error(`No Mach-O files found in embedded Python runtime: ${pythonRuntimeRoot}`);
  for (const binary of nestedBinaries) {
    run("codesign", ["--verify", "--strict", "--verbose=2", binary]);
    if (formalRelease) verifyDeveloperIdSignature(binary);
  }
  run("codesign", ["--verify", "--deep", "--strict", "--verbose=2", appBundle]);
  if (formalRelease) {
    verifyDeveloperIdSignature(appBundle);
    run("xcrun", ["stapler", "validate", appBundle]);
    run("spctl", ["--assess", "--type", "execute", "--verbose=4", appBundle]);
  }
}

if (!appBundles.length) throw new Error(`No macOS app bundle found in ${appDirectory}`);
for (const appBundle of appBundles) {
  verifyAppBundle(appBundle);
}

const bundlesIndex = buildArguments.indexOf("--bundles");
const requestedBundles = bundlesIndex >= 0 ? buildArguments[bundlesIndex + 1] || "" : "";
if (requestedBundles.split(",").includes("dmg")) {
  const diskImages = fs.existsSync(dmgDirectory)
    ? fs.readdirSync(dmgDirectory).filter((name) => name.endsWith(".dmg")).map((name) => path.join(dmgDirectory, name))
    : [];
  if (!diskImages.length) throw new Error(`No macOS disk image found in ${dmgDirectory}`);
  for (const diskImage of diskImages) {
    if (formalRelease) {
      run("codesign", ["--verify", "--verbose=2", diskImage]);
      verifyDeveloperIdSignature(diskImage);
      run("xcrun", ["stapler", "validate", diskImage]);
    }
    const mountPoint = fs.mkdtempSync(path.join(os.tmpdir(), "openrosalind-dmg-"));
    try {
      run("hdiutil", ["attach", "-nobrowse", "-readonly", "-mountpoint", mountPoint, diskImage]);
      const embeddedApps = fs.readdirSync(mountPoint)
        .filter((name) => name.endsWith(".app"))
        .map((name) => path.join(mountPoint, name));
      if (!embeddedApps.length) throw new Error(`No app bundle found inside ${diskImage}`);
      for (const appBundle of embeddedApps) {
        verifyAppBundle(appBundle);
      }
    } finally {
      spawnSync("hdiutil", ["detach", mountPoint], { stdio: "inherit" });
      fs.rmSync(mountPoint, { recursive: true, force: true });
    }
  }
}
