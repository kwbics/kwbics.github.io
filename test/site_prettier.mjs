// Check Git-tracked source only; never traverse generated/private trees.
import fs from "node:fs";
import { execFileSync } from "node:child_process";
import { createRequire } from "node:module";
import * as prettier from "prettier";

const require = createRequire(import.meta.url);
const lock = JSON.parse(fs.readFileSync("package-lock.json", "utf8"));
for (const name of ["prettier", "@shopify/prettier-plugin-liquid"]) {
  const installed = require(`${name}/package.json`).version;
  if (installed !== lock.packages[`node_modules/${name}`].version) {
    throw new Error(`${name} ${installed} differs from package-lock.json; run npm ci.`);
  }
}
const files = execFileSync("git", ["ls-files", "--cached", "-z"], { encoding: "utf8" }).split("\0").filter(Boolean);
let checked = 0;
let failures = 0;
for (const file of [...new Set(files)].sort()) {
  if (!fs.existsSync(file) || !fs.statSync(file).isFile()) continue;
  const info = await prettier.getFileInfo(file, { ignorePath: ".prettierignore", withNodeModules: false });
  if (info.ignored) continue;
  const config = await prettier.resolveConfig(file);
  const withPlugins = await prettier.getFileInfo(file, { ...config, ignorePath: ".prettierignore" });
  if (!withPlugins.inferredParser) continue;
  checked++;
  if (!(await prettier.check(fs.readFileSync(file, "utf8"), { ...config, filepath: file }))) {
    console.error(`[format] ${file}`);
    failures++;
  }
}
if (!checked) throw new Error("No source files were checked by Prettier.");
console.log(`[format] ${checked} source files checked; ${failures} need formatting.`);
process.exitCode = failures ? 1 : 0;
