import { existsSync, readFileSync, statSync } from 'node:fs'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { bacaEnv } from './env-file.ts'

/**
 * Penemuan akar repo + jalur aset, padanan `AKAR` dan `_temukan_persona()`
 * di `server_py/konfig.py`.
 *
 * Akar dicari dengan menaiki direktori sampai menemukan `pnpm-workspace.yaml`
 * (penanda monorepo). Ini menggantikan `Path(__file__).parent.parent` yang
 * rapuh terhadap posisi berkas.
 */
export function cariAkarRepo(dari: string = fileURLToPath(import.meta.url)): string {
  let dir = dirname(dari)
  for (let i = 0; i < 12; i++) {
    if (existsSync(join(dir, 'pnpm-workspace.yaml')) || existsSync(join(dir, '.git')))
      return dir
    const naik = dirname(dir)
    if (naik === dir)
      break
    dir = naik
  }
  return process.cwd()
}

/** Padanan `_temukan_persona()`: kandidat pertama yang ada, atau kandidat utama. */
export function temukanPersona(akar: string): string {
  const kandidat = [
    join(akar, 'silver_wolf_memory', 'persona.md'),
    join(akar, 'silver_wolf memory', 'persona.md'),
    join(akar, 'memori-waifu', 'persona.md'),
    join(akar, 'persona.md'),
  ]
  for (const p of kandidat) {
    if (existsSync(p) && statSync(p).isFile())
      return p
  }
  return join(akar, 'silver_wolf_memory', 'persona.md')
}

/** Baca `.env` di akar; kosong bila tidak ada. */
export function bacaEnvAkar(akar: string): Record<string, string> {
  const jalur = join(akar, '.env')
  if (!existsSync(jalur))
    return {}
  return bacaEnv(readFileSync(jalur, 'utf8'))
}

export const AKAR = cariAkarRepo()
export const AKAR_PERSONA = temukanPersona(AKAR)

/** Resolusi jalur relatif-akar (padanan `AKAR / "..."`). */
export function dariAkar(...bagian: string[]): string {
  return resolve(AKAR, ...bagian)
}
