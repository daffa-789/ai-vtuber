# AI VTuber

Teman desktop berbasis Live2D yang bisa diajak ngobrol lewat teks maupun suara,
menjawab dengan suara, dan menggerakkan wajah serta rahang sesuai isi pembicaraannya.

Status: renderer, loop chat, ekspresi, text-to-speech, dan memori jangka panjang sudah
berjalan. Memory karakter ditulis sebagai catatan Markdown di
vault Obsidian, jadi bisa dibaca dan disunting langsung.

## Menjalankan

Prasyarat: **Python 3.10** untuk aplikasi, dan **Node.js** hanya untuk skrip perkakas
(`scripts/*.js` — pemasangan model, pengunduh aset). Tidak ada `npm install`:
pustaka browser sudah divendur di `web/lib/` dan sisi server murni stdlib Python.

```bash
python -m venv .venv
.venv\Scripts\python.exe server_py\app.py    # satu-satunya proses yang perlu dijalankan
# buka http://127.0.0.1:8787/  (port ikut VTUBER_PORT di .env)
```

Sekali jalan dari nol — aset karakter tidak ikut ke git:

```bash
node scripts/fetch-assets.js     # Cubism core + aset VAD
node scripts/pasang-model.js     # sinkronkan konfigurasi ekspresi model penyihir
cp .env.example .env             # lalu isi GEMINI_API_KEY
```

Di halaman, ketik pesannya di kolom bawah. Jalur mikrofon **sedang dimatikan** —
pipingnya masih ada (`web/mikrofon.js`, `/api/stt`, aset VAD), tinggal disambung lagi.

## Arsitektur setelah rombakan Python

Yang dulu Node sekarang Python: satu proses `server_py/app.py` memegang API key, memanggil
Gemini (chat stream / TTS / STT), menulis memori ke vault, **dan** menyajikan halaman beserta
aset model. Tidak ada bundler, tidak ada dev server terpisah.

Yang tetap JavaScript: `web/*.js`. Bukan karena pilih — Live2D hanya bisa digambar di browser,
jadi Cubism Core, Pixi, dan `pixi-live2d-display` adalah JS/WASM. Ketiganya berkas UMD siap
pakai yang dimuat dengan `<script>` biasa, sehingga tidak ada langkah build sama sekali.

| Dahulu (Node + Vite) | Sekarang |
|---|---|
| `server/index.js` | `server_py/app.py` + `gemini.py` + `memori.py` + `vault.py` |
| `npm run dev` (Vite di :5173) | `server_py/statis.py` menyajikan `web/` dan `public/` |
| `import.meta.env.VITE_*` | `window.__VTUBER_ENV__`, disuntikkan Python ke `index.html` |
| `src/*.ts` + `tsconfig.json` | `web/*.js` — ESM asli browser |
| `node_modules` (270 MB) | `web/lib/` (647 KB: pixi + cubism4 + vad) |

Sisi Python sengaja **tanpa dependensi**: `requirements.txt` kosong, `.venv` hanya untuk
memisahkan interpreter. Parser resep wajah/pose tetap satu berkas (`web/konfigurasi.js`) yang
dipakai browser DAN skrip Node, supaya nilainya tidak mungkin beda di dua tempat.

## Model karakter

Karakternya model Live2D Cubism 4 (279 parameter, 617 art mesh, tekstur 8192),
dikelola di `public/models/penyihir/` dengan nama berkas dan konfigurasi bahasa Indonesia:

```
public/models/penyihir/
  penyihir.model3.json      daftar ekspresi + motion, ini yang dibaca aplikasi
  penyihir.moc3             geometri yang sudah dikompilasi (jangan disunting)
  penyihir.physics3.json    rambut, baju, perhiasan bergoyang
  penyihir.cdi3.json        label parameter untuk editor — sudah dialihbahasakan
  tekstur/texture_00.png    8192x8192
  tekstur/texture_01.png    4096x8192
  ekspresi/*.exp3.json      salinan dari resep di .env, untuk alat luar (VTube/Cubism)
  gerakan/sedih-melambai.motion3.json
```

Sembilan wajah tersusun rapi dari parameter modelnya dan dialihbahasakan ke Indonesia:
**Resepnya diatur fleksibel di `.env`** -- masing-masing adalah satu baris `VITE_WAJAH_*` /
`VITE_POSE_*` di `.env`, dan berkas `.exp3.json` di atas disinkronkan oleh `node scripts/pasang-model.js`.
Label parameter juga tersimpan rapi di `penyihir.cdi3.json`:

| Singkatan / Parameter | Arti sebenarnya | Dipakai untuk |
|---|---|---|
| `ku` | mata berair + alis naik | `sedih` |
| `sq` | cemberut | `sebal` |
| `h` | setetes keringat + bayangan muram di mata | `bingung` |
| `xx` / `x` | pupil bintang / pupil hati | `semangat` / `goda` |
| `mz` `fz` `yj` `zs1` `zs2` `cw` `hdj` | topi, tongkat sihir, kacamata, memamerkan barang, hantu kecil, kalung | kanal `[prop:...]`, ditumpuk di atas wajah |

`netral`, `senyum`, `kaget`, dan `lelah` tidak punya lapisan sendiri di model aslinya,
jadi keempatnya saya rakit dari parameter dasar (`ParamEyeLOpen`, `ParamBrowLY`,
`ParamMouthForm`, `Param50`). Rentang tiap parameter dibaca dari model yang sedang
berjalan, bukan ditebak.

Napass, goyang kepala, dan kedip tidak butuh berkas motion — pustaka `pixi-live2d-display`
sudah menyetelnya sendiri, dan itu alasan `gerakan/` sengaja tidak dipasang sebagai Idle:
kalau ada motion yang jalan, pustaka justru mematikan kedip otomatisnya.

## Diatur lewat .env

Semua yang bergerak, berubah wajah, dan mengukur piksel dibaca dari satu berkas:
`.env` isinya, `web/konfigurasi.js` parsernya — dipakai browser DAN
`node scripts/pasang-model.js`, jadi tidak bisa beda. Cara melihat apa yang sedang terpakai:

```bash
node scripts/tampilkan-konfigurasi.js            # tabel wajah/pose/gerakan + peringatan sintaks
node scripts/tampilkan-konfigurasi.js --env   # blok .env siap tempel dari nilai efektif
```

| Yang mau diubah | Kunci |
|---|---|
| Raut wajah (9) | `VITE_WAJAH_<NAMA>="ParamMouthForm=1 ParamEyeLOpen=-0.35"` |
| Pose / aksesoris (7) | `VITE_POSE_<NAMA>="Param72=30"`, tag `[prop:tongkat]` dan `[prop:tongkat=mati]` |
| Wajah saat dibuka dan lama pudarnya | `VITE_EKSPRESI_DASAR`, `VITE_PUDAR_WAJAH_MS` |
| Gerakan (motion) | `VITE_GERAK_<NAMA>="grup=isyarat berkas=... sumber=... ulang=false"` |
| Ukuran kotak avatar (CSS px) | `VITE_PANGGUNG_UKURAN`, `VITE_PANGGUNG_LEBAR`, `VITE_PANGGUNG_TINGGI` |
| Seberapa besar karakter mengisi kotak | `VITE_AVATAR_ZOOM`, `VITE_AVATAR_X`, `VITE_AVATAR_JANGKAR` |
| Jumlah piksel nyata / ketajaman | `VITE_RENDER_SKALA`, `VITE_RENDER_SKALA_MAKS`, `VITE_RENDER_HALUS` |
| Kedip, napas, kepala ikut kursor | `VITE_KEDIP`, `VITE_NAPAS`, `VITE_IKUTI_KURSOR` |
| Atlas tekstur yang dipasang | `VITE_TEKSTUR` (model ini sudah 8192, maksimum dari aslinya) |
| Berapa lama dia boleh menggambar (hemat GPU) | `VITE_IRAMA_JEDA_SAAT_SEMBUNYI`, `VITE_IRAMA_FPS_SAAT_TAK_FOKUS` |

Satu sintaks untuk semuanya: token `Id=Nilai` dipisah spasi; blend default `Add`
menambah di atas nilai bawaan parameter, `:Overwrite` menulis mentah, `:Multiply`
mengali; `kosong` berarti tanpa parameter. Nama kunci diterjemahkan apa adanya —
`VITE_POSE_HANTU_KECIL` menjadi pose `hantu-kecil`. Id yang tidak ada di model atau
nilai yang keluar rentang dilaporkan di status halaman ("N konfigurasi perlu dicek")
dan di log browser. Ubah nilainya cukup
muat ulang halaman; hanya gerakan baru yang perlu `node scripts/pasang-model.js` lagi
supaya berkasnya ikut dipasang.

Wajah memakai sistem ekspresi pustaka (satu wajah pada satu waktu), sedangkan pose
ditulis sebagai lapisan parameter paling akhir setiap frame — sehingga tongkat,
kacamata, atau hantu kecil tetap menempel walau wajahnya sedang sedih.

### Irama render: jangan menggambar untuk orang yang tidak melihat

Sebelum ada `web/iriama.js`, kanvas meminta frame secepat mungkin terus-menerus —
termasuk saat jendelanya tertutup jendela lain atau jadi overlay selalu-di-depan
yang sedang tidak dipandang. Pada Iris Xe itu berarti panas dan baterai. Dua knob:

| Knob | Arti | Bawaan |
|---|---|---|
| `VITE_IRAMA_JEDA_SAAT_SEMBUNYI` | `document.hidden` (tab latar, jendela diminimakan) → `ticker.stop()`: nol frame, tidak ada `requestAnimationFrame` yang tertinggal di antrean | `true` |
| `VITE_IRAMA_FPS_SAAT_TAK_FOKUS` | terlihat tapi tidak fokus → `ticker.maxFPS` dipasang ke angka ini; `0` = tidak dibatasi | `30` |

Yang **tidak** tersentuh suara: audio diputar elemen `<audio>` dan rahang dibaca
dari posisi audio itu, jadi saat halaman tersembunyi mulutnya membeku sementara
suaranya tetap jalan, dan begitu muncul lagi rahangnya langsung berada di fase yang
benar — bukan mengulang dari nol. `app.ticker` juga bukan ticker global, dan model
Live2D terdaftar di ticker itu, jadi satu `stop()` menghentikan pembaruan parameter
sekaligus penggambaran (terukur: 0 kali `internalModel.update` dalam 600 ms).

Satu temuan yang mengubah cara baca angka lama: "tab latar cuma 1 FPS" bukan
pencapaian hemat — itu Chromium yang memotong sendiri, dan dia melakukannya hanya
untuk tab. Jendela yang terlihat-tapi-tidak-fokus tetap 60 FPS, dan di mesin ini
Chrome bahkan tidak pernah melaporkan `hidden` untuk jendela yang diminimakan
(terukur `windowState=minimized`, `visibilityState=visible`, rAF tetap 60).
Jadi bagian yang benar-benar bekerja di hardware ini adalah batas 30 FPS saat tidak
fokus — itu juga yang dibutuhkan Fase 5, karena overlay selalu-di-depan tidak akan
pernah "tersembunyi".

### Kenapa avatar pernah terlihat burik saat di-zoom

Bukan tekstur: atlas model ini 8192 px, jauh di atas ukuran layar. Penyebabnya
kanvas WebGL — jumlah pikselnya ditetapkan sekali saat halaman dibuka, sementara
zoom browser mengubah `devicePixelRatio` setelahnya; browser kemudian merentangkan
gambar lama. Kini resolusinya dihitung ulang tiap rasio piksel berubah (media query
yang dipasang ulang setiap kali) dan tiap resize, jadi piksel nyata kanvas selalu
`ukuran CSS × devicePixelRatio`.

Kalau GPU mulai kalah, turunkan `VITE_RENDER_SKALA_MAKS` atau paksa satu angka lewat
`VITE_RENDER_SKALA`. Status halaman menampilkan `738×738 css · 886×886 px · 1.25×` —
kalau angka CSS dan piksel tidak sebanding, kanvas sedang diregangkan.

## Rupa panel

Rel kiri adalah dia; rel kanan adalah buku catatannya. Elaina menyendiri di jalan
dan mencatat apa yang dia lihat, dan memori build ini pun sungguh-sungguh berupa
catatan Markdown di vault — jadi panelnya sebuah ledger lapangan, bukan dashboard.

- **Warna.** Langit di atas laut awan (`#0d1119` → `#1e2739`) dengan satu aksen
  lampu minyak `#e8b673`. Amber dipakai hanya untuk yang hidup: raut aktif,
  cincin fokus, dan lampu bicara. `#c2707c` khusus galat.
- **Tipografi tanpa jaringan.** Palatino/Georgia untuk kepala, Segoe UI untuk baca,
  Cascadia/Consolas untuk angka mesin — semuanya sudah ada di Windows. Sengaja
  tidak ada tautan webfont: halaman ini harus tetap sama rupanya saat offline.
- **Lampu = `#suara`.** Titik di kanan atas menyala amber saat dia menyusun suara
  dan memerah saat TTS gugur. `chat.js` menulis teks *dan* `data-keadaan` lewat
  satu fungsi (`setSuara`) supaya keduanya tidak bisa berbeda.
- **Meteran `raut`.** Nama wajah yang sedang tampil, dibaca langsung dari
  `setEkspresi` — bukan dari tombol yang ditekan, karena wajah juga berganti lewat
  tag chat dan lewat ekspresi dasar.
- **Tidak ada animasi berulang.** Transisi 120–180ms saja, dan semuanya dimatikan
  untuk `prefers-reduced-motion`. Yang boleh bergerak terus cuma avatar-nya — dan
  `web/iriama.js` justru merampas hak itu saat dia tidak dilihat.

Desain panel responsif menjaga tata letak tetap proporsional: chip ekspresi dan kontrol
tetap rapi pada layar ringkas, indikator fokus jelas untuk keyboard accessibility,
dan kontras teks terjaga pada tema gelap.

## Cara kerja

```
papan ketik ---------------------------> teks --> Gemini Flash --> teks + [tag]
                                                                    |
                                                              ekspresi Live2D
                                                Gemini TTS -> WAV 24kHz
                                                         |
                                          AnalyserNode -> ParamMouthOpenY

(mikrofon -> VAD Silero -> STT masih terpasang di sisi server, tapi belum
 ada tombolnya di halaman — lihat catatan di bagian Menjalankan)
```

- **`server_py/app.py`** — satu proses untuk semuanya: API key, Gemini (chat/TTS/STT),
  memori, dan sajian halaman. Hanya listen di `127.0.0.1`, membungkus PCM mentah jadi WAV,
  dan mencoba berjenjang saat model utama kena 503/429.
- **`server_py/gemini.py`** — REST Gemini lewat stdlib. `alir()` membuka koneksi SEBELUM
  mengembalikan iterator; kalau tidak, kegagalan model utama tidak tertangkap dan fallback
  cadangan tidak pernah jalan.
- **`server_py/statis.py`** — pengganti dev server: `web/` lalu `public/`, MIME benar,
  query `?import` dibuang, dan jalur di luar akar ditolak.
- **`persona.md`** — sifat dan gaya bicara karakter. Ini konfigurasi, bukan model yang
  dilatih: diedit langsung, dan selalu dikirim sebagai system instruction.
- **`web/konfigurasi.js`** — parser `.env` (wajah, pose, gerakan, ukuran). Dipakai browser
  dan `scripts/pasang-model.js`, satu sumber kebenaran di dua runtime.
- **`web/wajah.js`** — menyuntik resep dari `.env` ke expression manager saat runtime
  dan menjaga lapisan pose tetap di atas wajah (`beforeModelUpdate`).
- **`web/ekspresi.js`** — gerbang tag: tahu nama wajah dan pose dari konfigurasi, mengenal
  kanal `[prop:...]`, dan mengupas tag itu dari layar saat teks masih mengalir.
- **`web/main.js`** — kanvas + resolusi (ikut `devicePixelRatio` terus-menerus), tombol
  panel dari `.env`, dan gerakan ulang parameter setelah motion selesai.
- **`web/mikrofon.js`** — VAD Silero di mesin ini; hanya potongan yang terdeteksi sebagai
  bicara yang dikirim untuk disalin. **Belum tersambung ke halaman** — tidak ada modul yang
  mengimpornya, jadi aset `public/vad` dan `public/ort` tidak pernah diunduh browser.
- **`web/suara.js`** — memutar WAV dan mengukur amplitudo per frame.
- **`server_py/vault.py`** — menulis/membaca catatan karakter ke vault Obsidian lewat Local
  REST API; token diambil dari `~/.qoder/settings.json`, bukan dari berkas di repo.
- **`server_py/memori.py`** — kebijakan memori: apa yang masuk prompt, bagaimana mood
  bergeser dari tag ekspresi, dan kapan fakta baru diekstrak.
- **Gerak mulut** tidak memakai penempatan fonem per kata, melainkan amplitudo
  audio yang sedang diputar, dan ditulis pada event `afterMotionUpdate` supaya
  tidak ditimpa animasi idle.

## Memori karakter

Dia tidak dilatih. Yang membuatnya terasa "ingat" adalah tiga catatan Markdown di
vault, yang dibaca ulang dan disuntikkan ke system prompt setiap kali menjawab:

```
Qoder Memory/Project/Desktop AI VTUBER/Karakter/
  Fakta.md              daftar hal yang dia ingat tentangmu
  Mood.md               valensi, energi, afinitas, jumlah pertukaran
  Riwayat/2026-09-23.md percakapan hari itu, satu baris per tukaran
```

Semuanya bisa kamu buka dan sunting langsung di Obsidian. Menghapus satu baris di
`Fakta.md` berarti dia benar-benar lupa hal itu pada balasan berikutnya.

Alur penulisannya: setiap balasan selesai → tag ekspresinya dibaca → mood bergeser
dan riwayat harian bertambah. Ekstraksi fakta memakai model dan hanya berjalan tiap
`VTUBER_JEDA_FAKTA` pertukaran, karena ia menambah satu panggilan API.

Mood bergeser dari tag yang dia pakai sendiri, tanpa panggilan tambahan: `[semangat]`
menaikkan valensi, `[sedih]` dan `[sebal]` menurunkannya, dan setiap pertukaran
menaikkan afinitas sedikit. Kalau valensinya jatuh, system prompt berikutnya berisi
"kamu lagi agak berat hari ini" — itu sebabnya nadanya berubah lintas sesi.

Kalau Obsidian sedang tidak jalan, memori dilewati dengan satu baris peringatan dan
percakapan tetap berjalan.

## Batas kuota yang nyata

Angka di bawah diukur langsung dengan kunci tingkat gratis ini, bukan asumsi.
Model mana yang "boleh" tergantung kunci: `models.list()` bisa memperlihatkan
model yang ternyata 404 saat dipakai.

| Model | Kepentingan | Terukur 2026-09-24 |
|---|---|---|
| `gemini-3.5-transcribe` | penyalin suara | **3 permintaan per menit** |
| `gemini-3.5-flash` | otak percakapan | **0/3 gagal** — 503 "high demand" |
| `gemini-3.5-flash-lite` | otak percakapan | 0/3 gagal — 503 |
| `gemini-flash-lite-latest` | otak percakapan | 1/3, dan yang lolos butuh 61 dtk |
| `gemini-2.5-flash`, `-lite` | otak percakapan | 404 — tidak dibuka untuk akun ini |
| **`gemini-3-flash-preview`** | otak percakapan | **3/3**, 3,7 / 4,2 / 21,9 dtk <- dipakai |
| `gemini-2.5-flash-preview-tts` | suara | **49-77 dtk** untuk 5 dtk audio <- ditinggalkan |
| **`gemini-3.8-flash-lite-tts`** | suara | **2,6-3,8 dtk** untuk 5 dtk audio <- dipakai |
| `gemini-3.8-flash-tts` | suara | 3,3-3,9 dtk (jadi `VTUBER_TTS_CADANGAN`) |

## Berapa lama sampai dia bersuara

Dulu: teks 5-25 dtk (sering 503) **lalu** sintesis 49-77 dtk = belasan sampai
puluhan detik diam. Sekarang `/api/chat` mencoba `VTUBER_MODEL` lalu setiap
`VTUBER_MODEL_CADANGAN` sampai ada yang menjawab (503 itu antrean sementara dan
berbeda per model), dan setiap kalimat yang sudah selesai langsung disintesis
tanpa menunggu jawaban lengkap:

```
token pertama  --->  SUARA PERTAMA TERDENGAR     selesai
   10,0 dtk                13,3 dtk            15,1 dtk   (2 potongan)
```

Mode per kalimat itu menambah satu panggilan TTS per kalimat. Kalau kunci sering
kena batas permintaan per menit, matikan dengan `VTUBER_TTS_PER_KALIMAT=false`.
Yang masih tidak bisa dihindari di tingkat gratis adalah jeda sebelum token
pertama — itu antrean di sisi Google, dan naik ke kunci berbayar adalah satu-satunya
perbaikan yang benar-benar besar di bagian itu.

## Perkakas & Pengelolaan

```bash
node scripts/fetch-assets.js         # unduh dependensi Cubism Core dan modul VAD
node scripts/pasang-model.js         # sinkronkan berkas ekspresi .exp3.json di public/models/penyihir/
node scripts/tampilkan-konfigurasi.js # periksa resep ekspresi, pose, dan motion dari .env
```

Semua skrip di `scripts/` memuat `.env` secara mandiri lewat `scripts/env.js`.
Seluruh pengujian fungsional, rendering, dan integrasi telah selesai dilaksanakan dan diverifikasi.

## Kredit

Aset dan pustaka pihak ketiga yang dipakai proyek ini, beserta pemiliknya:

- **Model karakter "Penyihir"** (`public/models/penyihir`) — model Cubism 4
  dengan konfigurasi, parameter, dan ekspresi berbahasa Indonesia.
- **Live2D Cubism Core for Web** (`live2dcubismcore.min.js`) — SDK resmi
  [Live2D Inc.](https://www.live2d.com/en/sdk/download/web/), *Cubism SDK License*.
- **[pixi-live2d-display](https://github.com/guansss/pixi-live2d-display)**
  oleh guansss — MIT.
- **[PixiJS](https://github.com/pixijs/pixijs)** — MIT. Renderer WebGL.
- **[vad-web](https://github.com/ricky0123/vad)** oleh ricky0123 — MIT. Pembungkus
  deteksi bicara untuk browser.
- **[Silero VAD](https://github.com/snakers4/silero-vad)** — MIT. Model deteksi
  suara yang benar-benar berjalan di mesinmu.
- **[ONNX Runtime Web](https://github.com/microsoft/onnxruntime)** — MIT.

Gemini API dipanggil langsung lewat REST dari stdlib Python, jadi tidak ada SDK yang
ikut ke proyek. Vite, TypeScript, dan `@google/genai` dipakai pada fase awal dan sudah
dihapus bersama `node_modules`, jadi tidak lagi menjadi bagian dari daftar ini.

Kode di repositori ini adalah karya proyek; seluruh aset dan pustaka di atas
tetap pada lisensinya masing-masing.

## Lisensi

Kode sumber proyek ini bebas dipakai sesuai ketentuan yang berlaku padanya.
**Model Live2D dan Cubism Core tidak termasuk** dan tidak diizinkan untuk
diredistribusi sebagai berkas lepas — karena itu keduanya dikecualikan dari
repositori dan diambil ulang dengan `node scripts/fetch-assets.js`. Untuk karakter publik,
gunakan model milik sendiri.
