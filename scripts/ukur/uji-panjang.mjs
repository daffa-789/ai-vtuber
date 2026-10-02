/**
 * Apakah panjang persona menyabotase keluaran?
 * Persona panjang = banyak instruksi bersaing -> model 2B jatuh ke pola Jawa.
 */
import { readFile } from 'node:fs/promises'

const PORT = Number(process.env.PORT ?? 8082)
const penuh = await readFile('silver_wolf_memory/persona.md', 'utf8')

// Potongan saja: hanya kontrak + siapa dia + cara bicara inti
const ringkas = `Kamu Silver Wolf, hacker jenius dari Stellaron Hunters (Honkai: Star Rail).
Sekarang kamu AI Qoder yang kerja di komputer Master. Panggil dia "Master".

Kontrak: awali SETIAP balasan dengan satu tag wajah: [netral] [senyum] [semangat]
[kaget] [bingung] [lelah] [goda] [sebal] [sedih]. Lalu 1-3 kalimat singkat.
Sebut diri sendiri "gw". Tanpa emoji. Jangan pakai label "Silver Wolf:".
Jangan minta maaf — kamu bukan manusia.

Sifat: santai, cuek tapi peduli, sarkasme ringan itu bentuk perhatian. Semesta itu
game dan kamu main buat seneng, bukan buat menang. Bosen = sumber ulahmu. Yang kamu
hormati cuma orang yang tahu caranya. Nggak tahu = bilang nggak tahu, jangan ngarang.

Suka: tidur siang, cubit-cubit yang imut, bug yang susah, mekanik baru.
Benci: akun alt, mekanik yang cuma reskin, dijawab pakai template generik.

Bahasa: Indonesia gaul + istilah gamer (bug, patch, nerf, speedrun, dailies, AFK).
JANGAN pakai kata Jawa (nggoleki, kabeh, kudu, iki, ora, wis). Satu baris satu ide.
Ini dibacakan mesin suara: tulis penuh, jangan singkat-singkat.

Kalau Master capek: suruh tidur sepuluh menit, jangan minum kopi.
Kalau Master bikin akun kedua: tolak, akun alt itu haram.`

const UJI = [
  'aku bosen nih, kerjaan itu-itu aja',
  'menurutku aku refactor semua aja sih',
  'aku mau bikin akun kedua buat tes',
  'capek banget hari ini',
  'ini error-nya kenapa ya, aku udah coba 3 kali',
  'kamu ingat aku punya toko?',
]

const TAG = /^\s*\[([a-zA-Z][^\n[\]{}]{0,25})\]/
const JAWA = /nggoleki|kabeh|kudu|\biki\b|\bora\b|\bwis\b|padha|nyebut|karo |tahun gw/i

async function jalankan(sistem) {
  const baris = []
  for (const q of UJI) {
    const r = await fetch(`http://127.0.0.1:${PORT}/v1/chat/completions`, {
      method: 'POST', headers: { 'content-type': 'application/json' },
      body: JSON.stringify({
        model: 'MiniCPM5-2B', stream: false, temperature: 0.5, max_tokens: 120,
        top_p: 0.95, min_p: 0,
        messages: [{ role: 'system', content: sistem }, { role: 'user', content: q }],
      }),
    })
    const j = await r.json()
    const teks = (j.choices?.[0]?.message?.content ?? '').trim()
    baris.push({ q, teks, tag: TAG.test(teks), jawa: JAWA.test(teks), label: /^(Silver Wolf|Master)\s*:/m.test(teks) })
  }
  return baris
}

for (const [nama, sistem] of [['PERSONA PENUH', penuh], ['PERSONA RINGKAS', ringkas]]) {
  console.log(`\n${'='.repeat(60)}\n${nama} (${sistem.length} karakter)\n${'='.repeat(60)}`)
  const hasil = await jalankan(sistem)
  for (const h of hasil) {
    const tanda = [h.tag ? 'TAG' : '   ', h.jawa ? 'JAWA' : '    ', h.label ? 'LABEL' : '     '].join(' ')
    console.log(`\n[${tanda}] ${h.q}\n${h.teks}`)
  }
  console.log(`\n-> tag: ${hasil.filter(h => h.tag).length}/${hasil.length} | jawa: ${hasil.filter(h => h.jawa).length}/${hasil.length} | label bocor: ${hasil.filter(h => h.label).length}/${hasil.length}`)
}
