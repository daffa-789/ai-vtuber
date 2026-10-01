import { EMOTION_TAGS, type EmotionTag } from './mood.ts'

const dikenal = new Set<string>(EMOTION_TAGS)
// Harus berada di awal. Dengan begitu arr[0] atau blok kode tidak dikira tag wajah.
const TAG_AWAL = /^[\s`'"]*\[([a-zA-Z][^\n[\]{}]{0,25})\][\s`'"]*/

export function bacaTagAwal(teks: string): EmotionTag | undefined {
  const tag = TAG_AWAL.exec(teks)?.[1]?.trim().toLowerCase()
  return tag && dikenal.has(tag) ? tag as EmotionTag : undefined
}

export function bersihkanTagAwal(teks: string): { teks: string; tag?: EmotionTag } {
  const tag = bacaTagAwal(teks)
  if (!tag) return { teks }
  return { teks: teks.replace(TAG_AWAL, ''), tag }
}
