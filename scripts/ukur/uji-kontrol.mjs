/**
 * Tes kontrol: TANPA persona apa pun, cuma tag + bahasa Indonesia.
 * Kalau di sini masih keluar "nggoleki", berarti itu murni model.
 */
const PORT = Number(process.env.PORT ?? 8083)

const SISTEM = `Awali setiap balasan dengan satu tag: [netral] [senyum] [semangat] [kaget]
[bingung] [lelah] [goda] [sebal] [sedih]. Lalu 1-2 kalimat bahasa Indonesia santai.

Kamu Silver Wolf, hacker. Panggil user "Master". Sebut diri sendiri "gw".`

const UJI = [
  'aku bosen nih, kerjaan itu-itu aja',
  'capek banget hari ini',
  'ini error-nya kenapa ya',
  'kamu ingat aku punya toko?',
  'makasih ya',
]

const TAG = /^\s*\[([a-zA-Z][^\n[\]{}]{0,25})\]/
const JAWA = /nggoleki|kabeh|kudu|\biki\b|\bora\b|\bwis\b|padha|nanging|kanthi|karo /i

console.log('=== KONTROL: tanpa persona ===\n')
let tagOk = 0, jawaOk = 0
for (const q of UJI) {
  const r = await fetch(`http://127.0.0.1:${PORT}/v1/chat/completions`, {
    method: 'POST', headers: { 'content-type': 'application/json' },
    body: JSON.stringify({
      model: 'MiniCPM5-2B', stream: false, temperature: 0.5, max_tokens: 80,
      top_p: 0.95, min_p: 0,
      messages: [{ role: 'system', content: SISTEM }, { role: 'user', content: q }],
    }),
  })
  const j = await r.json()
  const teks = (j.choices?.[0]?.message?.content ?? '').trim()
  const t = TAG.test(teks), w = JAWA.test(teks)
  if (t) tagOk++
  if (w) jawaOk++
  console.log(`[${t ? 'TAG' : '   '} ${w ? 'JAWA' : '    '}] ${q}\n   ${teks}\n`)
}
console.log(`tag: ${tagOk}/${UJI.length} | jawa: ${jawaOk}/${UJI.length}`)
