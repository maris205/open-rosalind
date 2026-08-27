import { spawnSync } from "node:child_process";
import { createHash } from "node:crypto";
import {
  existsSync,
  mkdirSync,
  mkdtempSync,
  readFileSync,
  readdirSync,
  renameSync,
  rmSync,
  writeFileSync
} from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

if (process.platform !== "darwin") {
  throw new Error("The embedded macOS Python runtime can only be prepared on macOS.");
}

const desktopRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const scriptPath = fileURLToPath(import.meta.url);
const manifestPath = path.join(desktopRoot, "python-runtime-manifest.json");
const lockPath = path.join(desktopRoot, "requirements-runtime.lock");
const runtimeRoot = path.join(desktopRoot, "python-runtime");
const manifest = JSON.parse(readFileSync(manifestPath, "utf8"));
const lockSha256 = sha256(lockPath);
const force = process.env.OPENROSALIND_FORCE_RUNTIME === "1";
const requestedArch = readArgument("--arch") || process.arch;
const architectures = requestedArch === "universal"
  ? ["arm64", "x64"]
  : [normalizeArchitecture(requestedArch)];

for (const architecture of architectures) {
  if (!manifest.macos?.[architecture]) {
    throw new Error(`No embedded Python runtime is configured for ${architecture}.`);
  }
}

mkdirSync(runtimeRoot, { recursive: true });
for (const entry of readdirSync(runtimeRoot, { withFileTypes: true })) {
  if (entry.isDirectory() && ["arm64", "x64"].includes(entry.name) && !architectures.includes(entry.name)) {
    rmSync(path.join(runtimeRoot, entry.name), { recursive: true, force: true });
  }
}

for (const architecture of architectures) {
  prepareArchitecture(architecture);
}

function readArgument(name) {
  const index = process.argv.indexOf(name);
  return index >= 0 ? process.argv[index + 1] : undefined;
}

function normalizeArchitecture(value) {
  const normalized = ({ aarch64: "arm64", arm64: "arm64", x86_64: "x64", x64: "x64" })[value];
  if (!normalized) throw new Error(`Unsupported macOS Python architecture: ${value}`);
  return normalized;
}

function sha256(filePath) {
  return createHash("sha256").update(readFileSync(filePath)).digest("hex");
}

function run(command, args, options = {}) {
  const result = spawnSync(command, args, { stdio: "inherit", ...options });
  if (result.error) throw result.error;
  if (result.status !== 0) {
    throw new Error(`${command} exited with status ${result.status}`);
  }
}

function capture(command, args, options = {}) {
  const result = spawnSync(command, args, { encoding: "utf8", ...options });
  if (result.error) throw result.error;
  if (result.status !== 0) {
    process.stderr.write(result.stderr || "");
    throw new Error(`${command} exited with status ${result.status}`);
  }
  return result.stdout.trim();
}

function removePythonBytecode(directory) {
  if (!existsSync(directory)) return;
  for (const entry of readdirSync(directory, { withFileTypes: true })) {
    const entryPath = path.join(directory, entry.name);
    if (entry.isDirectory() && entry.name === "__pycache__") {
      rmSync(entryPath, { recursive: true, force: true });
    } else if (entry.isDirectory()) {
      removePythonBytecode(entryPath);
    } else if (entry.isFile() && entry.name.endsWith(".pyc")) {
      rmSync(entryPath, { force: true });
    }
  }
}

function runtimeStamp(architecture, asset) {
  return {
    schema: 1,
    provider: manifest.provider,
    release: manifest.release,
    pythonVersion: manifest.pythonVersion,
    architecture,
    asset: asset.asset,
    assetSha256: asset.sha256,
    requirementsSha256: lockSha256,
    preparationScriptSha256: sha256(scriptPath)
  };
}

function stampMatches(target, expected) {
  const stampPath = path.join(target, ".openrosalind-embedded-runtime.json");
  if (!existsSync(stampPath)) return false;
  try {
    const current = JSON.parse(readFileSync(stampPath, "utf8"));
    return Object.entries(expected).every(([key, value]) => current[key] === value);
  } catch {
    return false;
  }
}

function probeRuntime(target, architecture) {
  const python = path.join(target, "bin", "python3");
  if (!existsSync(python)) throw new Error(`Embedded Python executable is missing: ${python}`);
  const result = JSON.parse(capture(python, [
    "-I",
    "-B",
    "-c",
    "import json, platform, ssl, sqlite3; import docx, lxml, pypdf, redis, rq, sqlalchemy; print(json.dumps({'version': platform.python_version(), 'machine': platform.machine(), 'openssl': ssl.OPENSSL_VERSION, 'sqlite': sqlite3.sqlite_version}))"
  ], { env: { ...process.env, PYTHONDONTWRITEBYTECODE: "1", PYTHONNOUSERSITE: "1", PYTHONSAFEPATH: "1" } }));
  const actualArchitecture = normalizeArchitecture(result.machine);
  if (actualArchitecture !== architecture) {
    throw new Error(`Embedded Python architecture is ${result.machine}, expected ${architecture}.`);
  }
  if (result.version !== manifest.pythonVersion) {
    throw new Error(`Embedded Python version is ${result.version}, expected ${manifest.pythonVersion}.`);
  }
  return result;
}

function prepareArchitecture(architecture) {
  const asset = manifest.macos[architecture];
  const target = path.join(runtimeRoot, architecture);
  const expectedStamp = runtimeStamp(architecture, asset);

  if (!force && stampMatches(target, expectedStamp)) {
    removePythonBytecode(target);
    const probe = probeRuntime(target, architecture);
    console.log(`Embedded Python is up to date: ${architecture} ${probe.version}`);
    return;
  }

  const cacheRoot = path.join(os.homedir(), "Library", "Caches", "OpenRosalind", "python-runtime");
  mkdirSync(cacheRoot, { recursive: true });
  const archive = path.join(cacheRoot, asset.asset);
  if (existsSync(archive) && sha256(archive) !== asset.sha256) {
    rmSync(archive, { force: true });
  }
  if (!existsSync(archive)) {
    const url = `https://github.com/${manifest.provider}/releases/download/${manifest.release}/${asset.asset}`;
    console.log(`Downloading verified Python runtime for ${architecture}...`);
    run("curl", ["--fail", "--location", "--retry", "3", "--output", archive, url]);
  }
  const actualHash = sha256(archive);
  if (actualHash !== asset.sha256) {
    throw new Error(`Python runtime checksum mismatch for ${asset.asset}: ${actualHash}`);
  }

  const stagingRoot = mkdtempSync(path.join(os.tmpdir(), `openrosalind-python-${architecture}-`));
  try {
    run("tar", ["-xzf", archive, "-C", stagingRoot]);
    const stagedRuntime = path.join(stagingRoot, "python");
    const python = path.join(stagedRuntime, "bin", "python3");
    if (!existsSync(python)) throw new Error(`Archive ${asset.asset} did not contain python/bin/python3`);
    run(python, [
      "-I",
      "-B",
      "-m", "pip", "install",
      "--disable-pip-version-check",
      "--no-compile",
      "--only-binary=:all:",
      "--require-hashes",
      "--upgrade",
      "-r", lockPath
    ], { env: { ...process.env, PYTHONDONTWRITEBYTECODE: "1", PYTHONNOUSERSITE: "1", PYTHONSAFEPATH: "1" } });
    removePythonBytecode(stagedRuntime);
    const probe = probeRuntime(stagedRuntime, architecture);
    writeFileSync(
      path.join(stagedRuntime, ".openrosalind-embedded-runtime.json"),
      `${JSON.stringify({ ...expectedStamp, preparedAt: new Date().toISOString(), probe }, null, 2)}\n`
    );
    rmSync(target, { recursive: true, force: true });
    renameSync(stagedRuntime, target);
    console.log(`Prepared embedded Python: ${architecture} ${probe.version} at ${target}`);
  } finally {
    rmSync(stagingRoot, { recursive: true, force: true });
  }
}
