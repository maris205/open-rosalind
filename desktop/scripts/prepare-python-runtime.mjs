import { spawnSync } from "node:child_process";
import { createHash } from "node:crypto";
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const desktopRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const repositoryRoot = resolve(desktopRoot, "..");
const target = resolve(desktopRoot, "python-packages");
const requirements = resolve(repositoryRoot, "requirements.txt");
const stampPath = resolve(target, ".openrosalind-runtime.json");
const python = process.env.OPENROSALIND_PYTHON || (process.platform === "win32" ? "python" : "python3");
const force = process.env.OPENROSALIND_FORCE_RUNTIME === "1";

const requirementsHash = createHash("sha256")
  .update(readFileSync(requirements))
  .digest("hex");

if (!force && existsSync(stampPath)) {
  try {
    const stamp = JSON.parse(readFileSync(stampPath, "utf8"));
    if (
      stamp.schema === 1 &&
      stamp.python === python &&
      stamp.requirementsSha256 === requirementsHash &&
      stamp.platform === process.platform
    ) {
      console.log(`Python runtime is up to date: ${target}`);
      process.exit(0);
    }
  } catch {
    // A partial or old stamp is harmless; pip will recreate the runtime.
  }
}

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

writeFileSync(stampPath, `${JSON.stringify({
  schema: 1,
  python,
  platform: process.platform,
  requirementsSha256: requirementsHash,
  preparedAt: new Date().toISOString()
}, null, 2)}\n`);
console.log(`Prepared Python runtime: ${target}`);
