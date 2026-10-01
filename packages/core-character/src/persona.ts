import { readFile } from 'node:fs/promises'
export async function bacaPersona(path: string): Promise<string> {
  try { return await readFile(path, 'utf8') }
  catch (error) {
    if ((error as NodeJS.ErrnoException).code === 'ENOENT')
      throw new Error(`persona tidak ditemukan: ${path}`)
    throw error
  }
}
