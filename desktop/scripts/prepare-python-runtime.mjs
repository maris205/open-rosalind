import { spawnSync } from "node:child_process";
import { createHash } from "node:crypto";
import { existsSync, mkdirSync, readdirSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const desktopRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const repositoryRoot = resolve(desktopRoot, "..");
const target = resolve(desktopRoot, "python-packages");
const requirements = resolve(repositoryRoot, "requirements.txt");
const stampPath = resolve(target, ".openrosalind-runtime.json");
const python = process.env.OPENROSALIND_PYTHON || (process.platform === "win32" ? "python" : "python3");
const force = process.env.OPENROSALIND_FORCE_RUNTIME === "1";

function removePythonBytecode(directory) {
  if (!existsSync(directory)) return;
  for (const entry of readdirSync(directory, { withFileTypes: true })) {
    const entryPath = resolve(directory, entry.name);
    if (entry.isDirectory() && entry.name === "__pycache__") {
      rmSync(entryPath, { recursive: true, force: true });
    } else if (entry.isDirectory()) {
      removePythonBytecode(entryPath);
    } else if (entry.isFile() && entry.name.endsWith(".pyc")) {
      rmSync(entryPath, { force: true });
    }
  }
}

const probe = spawnSync(python, [
  "-c",
  "import json, platform, sys; print(json.dumps({'executable': sys.executable, 'machine': platform.machine(), 'version': platform.python_version(), 'version_info': list(sys.version_info[:2])}))"
], { encoding: "utf8" });

if (probe.error) throw probe.error;
if (probe.status !== 0) {
  process.stderr.write(probe.stderr || `Unable to inspect Python runtime: ${python}\n`);
  process.exit(probe.status || 1);
}

const pythonInfo = JSON.parse(probe.stdout.trim());
const [pythonMajor, pythonMinor] = pythonInfo.version_info;
if (pythonMajor < 3 || (pythonMajor === 3 && pythonMinor < 10)) {
  throw new Error(`OpenRosalind Desktop requires Python 3.10+, found ${pythonInfo.version} at ${pythonInfo.executable}`);
}

const normalizedPythonArch = ({ arm64: "arm64", aarch64: "arm64", x86_64: "x64", AMD64: "x64" })[pythonInfo.machine];
if (process.platform === "darwin" && normalizedPythonArch && normalizedPythonArch !== process.arch) {
  throw new Error(`Node (${process.arch}) and Python (${normalizedPythonArch}) architectures do not match. Avoid mixing Rosetta and native runtimes.`);
}

const requirementsHash = createHash("sha256")
  .update(readFileSync(requirements))
  .digest("hex");

if (!force && existsSync(stampPath)) {
  try {
    const stamp = JSON.parse(readFileSync(stampPath, "utf8"));
    if (
      stamp.schema === 2 &&
      stamp.pythonExecutable === pythonInfo.executable &&
      stamp.pythonVersion === pythonInfo.version &&
      stamp.pythonMachine === pythonInfo.machine &&
      stamp.nodeArch === process.arch &&
      stamp.requirementsSha256 === requirementsHash &&
      stamp.platform === process.platform
    ) {
      removePythonBytecode(target);
      console.log(`Python runtime is up to date: ${target}`);
      process.exit(0);
    }
  } catch {
    // A partial or old stamp is harmless; pip will recreate the runtime.
  }
}

// A changed Python version or CPU architecture can leave incompatible native
// modules in a shared --target directory. Recreate it before installing.
rmSync(target, { recursive: true, force: true });
mkdirSync(target, { recursive: true });
const result = spawnSync(python, [
  "-m", "pip", "install",
  "--disable-pip-version-check",
  "--upgrade",
  "--target", target,
  "-r", requirements
], { stdio: "inherit" });

if (result.error) throw result.error;
if (result.status !== 0) process.exit(result.status || 1);
removePythonBytecode(target);

writeFileSync(stampPath, `${JSON.stringify({
  schema: 2,
  pythonExecutable: pythonInfo.executable,
  pythonVersion: pythonInfo.version,
  pythonMachine: pythonInfo.machine,
  nodeArch: process.arch,
  platform: process.platform,
  requirementsSha256: requirementsHash,
  preparedAt: new Date().toISOString()
}, null, 2)}\n`);
console.log(`Prepared Python runtime: ${target}`);
