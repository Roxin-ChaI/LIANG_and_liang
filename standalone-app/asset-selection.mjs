import fs from "node:fs/promises";
import path from "node:path";

/** Project-only asset selection. Packaged builds already contain selected bytes. */
export async function createAssetReader(root) {
  let mappings = {};
  try {
    mappings = JSON.parse(await fs.readFile(path.join(root, "standalone-app/asset-overrides.json"), "utf8"));
  } catch (error) {
    if (error.code !== "ENOENT") throw error;
  }
  for (const [logical, selected] of Object.entries(mappings)) {
    for (const value of [logical, selected]) {
      if (typeof value !== "string" || !value.startsWith("assets/") || value.split(/[\\/]/).includes("..")) {
        throw new Error("asset selection must remain inside project assets");
      }
    }
  }
  return async (filename, options) => {
    const relative = path.relative(root, filename).split(path.sep).join("/");
    const selected = mappings[relative];
    if (selected) {
      const actual = await fs.realpath(path.join(root, selected));
      if (!actual.startsWith(path.resolve(root) + path.sep)) throw new Error("asset symlink escapes project");
      return fs.readFile(actual, options);
    }
    return fs.readFile(filename, options);
  };
}
