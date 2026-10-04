import { existsSync, readFileSync, statSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { bacaEnv } from "./env-file.js";
function cariAkarRepo(dari = fileURLToPath(import.meta.url)) {
  let dir = dirname(dari);
  for (let i = 0; i < 12; i++) {
    if (existsSync(join(dir, "package.json")) || existsSync(join(dir, ".git")))
      return dir;
    const naik = dirname(dir);
    if (naik === dir)
      break;
    dir = naik;
  }
  return process.cwd();
}
function temukanPersona(akar) {
  const kandidat = [
    join(akar, "silver_wolf_memory", "persona.md"),
    join(akar, "silver_wolf memory", "persona.md"),
    join(akar, "memori-waifu", "persona.md"),
    join(akar, "persona.md")
  ];
  for (const p of kandidat) {
    if (existsSync(p) && statSync(p).isFile())
      return p;
  }
  return join(akar, "silver_wolf_memory", "persona.md");
}
function bacaEnvAkar(akar) {
  const jalur = join(akar, ".env");
  if (!existsSync(jalur))
    return {};
  return bacaEnv(readFileSync(jalur, "utf8"));
}
const AKAR = cariAkarRepo();
const AKAR_PERSONA = temukanPersona(AKAR);
function dariAkar(...bagian) {
  return resolve(AKAR, ...bagian);
}
export {
  AKAR,
  AKAR_PERSONA,
  bacaEnvAkar,
  cariAkarRepo,
  dariAkar,
  temukanPersona
};
