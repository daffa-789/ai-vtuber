/**
 * Buktikan: keluaran ngawur itu batas MODEL, bukan salah persona.
 *
 * Tiga kondisi diuji dengan pertanyaan yang sama:
 *  A. tanpa persona, minta bahasa Indonesia
 *  B. persona RAMPING (yang sekarang) + permintaan bahasa Indonesia tegas
 *  C. persona RAMPING, suhu rendah
 *
 * Kalau A pun sudah rusak, berarti masalahnya model.
 */
import { readFile } from 'node:fs/promises'

const PORT = Number(process.env.PORT ?? 8082)
const persona = await readFile('silver_wolf_memory/persona.md', 'utf8')
const Q = 'Apa itu variabel dalam pemrograman? Satu kalimat aja.'

async function tanya(sistem, suhu) {
  const r = await fetch(`http://127.0.0.1:${PORT}/v1/chat/completions`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({
      model: 'MiniCPM5-2B', stream: false, temperature: suhu, max_tokens: 70,
      top_p: 0.95, min_p: 0,
      messages: [{ role: 'system', content: sistem }, { role: 'user', content: Q }],
    }),
  })
  const j = await r.json()
  return (j.choices?.[0]?.message?.content ?? '').trim()
}

const KASUS = [
  ['A. tanpa persona, t=0.3', 'Jawab dalam bahasa Indonesia yang baik dan benar.', 0.3],
  ['B. persona ramping, t=0.3', persona, 0.3],
  ['C. persona ramping, t=0.7', persona, 0.7],
  ['D. persona ramping, t=0.0', persona, 0.0],
]

for (const [nama, sistem, suhu] of KASUS) {
  const hasil = await tanya(sistem, suhu)
  const jawa = /nggoleki|kabeh|kudu|iki|tahun|padha|nyebut|karo |wis |ora /i.test(hasil)
  console.log(`\n### ${nama}`)
  console.log(hasil)
  console.log(`   -> indikasi Jawa: ${jawa ? 'YA' : 'tidak'}`)
}
