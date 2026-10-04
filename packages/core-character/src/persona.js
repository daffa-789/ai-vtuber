import { readFile } from "node:fs/promises";
async function bacaPersona(path) {
  try {
    return await readFile(path, "utf8");
  } catch (error) {
    if (error.code === "ENOENT")
      throw new Error(`persona tidak ditemukan: ${path}`);
    throw error;
  }
}
export {
  bacaPersona
};
