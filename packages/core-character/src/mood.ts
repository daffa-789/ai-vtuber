export const EMOTION_TAGS = [
  'netral', 'senyum', 'semangat', 'kaget', 'bingung', 'lelah', 'goda', 'sebal', 'sedih',
] as const
export type EmotionTag = typeof EMOTION_TAGS[number]

export interface Mood {
  valensi: number
  energi: number
  afinitas: number
  pertukaran: number
  alasan?: string
}

export const MOOD_AWAL: Readonly<Mood> = {
  valensi: 0.2,
  energi: 0.6,
  afinitas: 0.3,
  pertukaran: 0,
}

const NILAI_TAG: Partial<Record<EmotionTag, number>> = {
  senyum: 0.25, semangat: 0.35, goda: 0.2, netral: 0, bingung: -0.05,
  kaget: 0, lelah: -0.2, sedih: -0.3, sebal: -0.25,
}
const jepit = (n: number, min: number, maks: number) => Math.min(maks, Math.max(min, n))

export function perbaruiMood(lama: Mood | undefined, tag?: EmotionTag): Mood {
  const dasar = lama ?? MOOD_AWAL
  const delta = NILAI_TAG[tag ?? 'netral'] ?? 0
  return {
    valensi: jepit(dasar.valensi * 0.8 + delta * 0.5, -1, 1),
    energi: jepit(dasar.energi * 0.95 + (tag === 'semangat' ? 0.1 : 0) - 0.02, 0, 1),
    afinitas: jepit(dasar.afinitas + 0.03, 0, 1),
    pertukaran: dasar.pertukaran + 1,
    alasan: `tag terakhir: ${tag ?? 'tidak ada'}`,
  }
}

export function suasana(mood?: Mood): string {
  if (!mood) return ''
  if (mood.valensi < -0.25) return 'Kamu lagi agak berat hari ini, jadi jawabanmu lebih pendek dan lebih jujur.'
  if (mood.valensi > 0.3 && mood.energi > 0.5) return 'Kamu lagi ceria, boleh lebih usil sedikit.'
  if (mood.energi < 0.3) return 'Kamu lagi capek, bicaranya lebih pelan dan pendek.'
  return ''
}
