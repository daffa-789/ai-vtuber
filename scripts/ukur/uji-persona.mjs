/**
 * Uji persona baru: apakah tag keluar di AWAL, apakah nada Silver Wolf nyangkut,
 * apakah kosakata terlarang (cokelat/kopi/akun asli) tidak muncul.
 */
import { readFile } from 'node:fs/promises'

const PORT = Number(process.env.PORT ?? 8082)
const persona = await readFile('silver_wolf_memory/persona.md', 'utf8')

const UJI = [
  'aku bosen nih, kerjaan itu-itu aja',
  'menurutku aku refactor semua aja sih',
  'aku mau bikin akun kedua buat tes',
  'kamu suka kopi ya?',
  'capek banget hari ini',
  'ini error-nya kenapa ya, aku udah coba 3 kali',
  'makasih ya udah bantuin',
  'kamu ingat aku punya toko?',
]

const TAG = /^[\s`'"]*\[([a-zA-Z][^\n[\]{}]{0,25})\]/
const HARAM = ['cokelat', 'kopi', 'umur', 'nama asli', 'genius society']

async function tanya(q) {
  const r = await fetch(`http://127.0.0.1:${PORT}/v1/chat/completions`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({
      model: 'MiniCPM5-2B', stream: false, temperature: 0.7, top_p: 0.95, min_p: 0,
      max_tokens: 160,
      messages: [{ role: 'system', content: persona }, { role: 'user', content: q }],
    }),
  })
  if (!r.ok) throw new Error(`HTTP ${r.status}: ${await r.text()}`)
  const j = await r.json()
  return (j.choices?.[0]?.message?.content ?? '').trim()
}

let tagAwal = 0
const hasil = []
for (const q of UJI) {
  const teks = await tanya(q)
  const m = TAG.exec(teks)
  if (m) tagAwal++
  const haram = HARAM.filter(h => teks.toLowerCase().includes(h))
  hasil.push({ q, teks, tag: m?.[1] ?? null, haram })
}

console.log('=== HASIL UJI PERSONA ===\n')
for (const h of hasil) {
  console.log(`T: ${h.q}`)
  console.log(`SW: ${h.teks}`)
  console.log(`   tag=${h.tag ?? 'TIDAK ADA'}${h.haram.length ? `  HARAM=${h.haram.join(',')}` : ''}\n`)
}
console.log(`tag di awal: ${tagAwal}/${hasil.length}`)
const panjang = hasil.reduce((a, h) => a + h.teks.length, 0) / hasil.length
console.log(`rata-rata panjang balasan: ${panjang.toFixed(0)} karakter`)
const kena = hasil.filter(h => h.haram.length).length
console.log(`balasan menyentuh topik haram: ${kena}/${hasil.length}`)
