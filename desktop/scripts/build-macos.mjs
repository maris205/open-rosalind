import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

if (process.platform !== "darwin") {
  throw new Error("The macOS bundle command must run on macOS.");
}

const desktopRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const tauri = path.join(desktopRoot, "node_modules", ".bin", "tauri");
const environment = { ...process.env };
const buildArguments = process.argv.slice(2);

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

const result = spawnSync(tauri, ["build", ...buildArguments], {
  cwd: desktopRoot,
  env: environment,
  stdio: "inherit"
});

if (result.error) throw result.error;
if (result.status !== 0) process.exit(result.status ?? 1);

const targetIndex = buildArguments.indexOf("--target");
const targetName = targetIndex >= 0 ? buildArguments[targetIndex + 1] : "";
const releaseRoot = targetName
  ? path.join(desktopRoot, "src-tauri", "target", targetName, "release")
  : path.join(desktopRoot, "src-tauri", "target", "release");
const bundleRoot = path.join(releaseRoot, "bundle");
const appDirectory = path.join(bundleRoot, "macos");
const dmgDirectory = path.join(bundleRoot, "dmg");
const appBundles = fs.existsSync(appDirectory)
  ? fs.readdirSync(appDirectory).filter((name) => name.endsWith(".app")).map((name) => path.join(appDirectory, name))
  : [];

if (!appBundles.length) throw new Error(`No macOS app bundle found in ${appDirectory}`);
for (const appBundle of appBundles) {
  run("codesign", ["--verify", "--deep", "--strict", "--verbose=2", appBundle]);
}

const bundlesIndex = buildArguments.indexOf("--bundles");
const requestedBundles = bundlesIndex >= 0 ? buildArguments[bundlesIndex + 1] || "" : "";
if (requestedBundles.split(",").includes("dmg")) {
  const diskImages = fs.existsSync(dmgDirectory)
    ? fs.readdirSync(dmgDirectory).filter((name) => name.endsWith(".dmg")).map((name) => path.join(dmgDirectory, name))
    : [];
  if (!diskImages.length) throw new Error(`No macOS disk image found in ${dmgDirectory}`);
  for (const diskImage of diskImages) {
    const mountPoint = fs.mkdtempSync(path.join(os.tmpdir(), "openrosalind-dmg-"));
    try {
      run("hdiutil", ["attach", "-nobrowse", "-readonly", "-mountpoint", mountPoint, diskImage]);
      const embeddedApps = fs.readdirSync(mountPoint)
        .filter((name) => name.endsWith(".app"))
        .map((name) => path.join(mountPoint, name));
      if (!embeddedApps.length) throw new Error(`No app bundle found inside ${diskImage}`);
      for (const appBundle of embeddedApps) {
        run("codesign", ["--verify", "--deep", "--strict", "--verbose=2", appBundle]);
      }
    } finally {
      spawnSync("hdiutil", ["detach", mountPoint], { stdio: "inherit" });
      fs.rmSync(mountPoint, { recursive: true, force: true });
    }
  }
}
