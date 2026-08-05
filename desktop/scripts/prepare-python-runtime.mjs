import { spawnSync } from "node:child_process";
import { mkdirSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const desktopRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const repositoryRoot = resolve(desktopRoot, "..");
const target = resolve(desktopRoot, "python-packages");
const python = process.env.OPENROSALIND_PYTHON || (process.platform === "win32" ? "python" : "python3");

mkdirSync(target, { recursive: true });
const result = spawnSync(python, [
  "-m", "pip", "install",
  "--disable-pip-version-check",
  "--upgrade",
  "--target", target,
  "-r", resolve(repositoryRoot, "requirements.txt")
], { stdio: "inherit" });

if (result.error) throw result.error;
if (result.status !== 0) process.exit(result.status || 1);
