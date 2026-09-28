# AI VTuber

Teman desktop berbasis Live2D yang bisa diajak ngobrol lewat teks maupun suara,
menjawab dengan suara, dan menggerakkan wajah serta rahang sesuai isi pembicaraannya.

Status: renderer Live2D, loop chat lokal (Llama 3.2 3B GGUF di CPU **atau** GPU
terintegrasi), ekspresi, text-to-speech lokal (Piper + RVC Furina), **mic lokal
(Whisper)**, dan memori jangka panjang Obsidian sudah berjalan.

**100% offline.** Chat, suara, dan mic dihitung di mesin ini; tidak ada satu pun
jalur runtime yang membuka koneksi ke luar. Yang masih butuh internet hanya
mendatangkan aset/binary ke mesin ini (lihat "Aset" di bawah) -- dan setelah itu ada
di disk, server tidak pernah memanggilnya lagi.

## Menjalankan

Prasyarat: **Python 3.10**. Tidak ada Node lagi di proyek ini — yang tersisa hanya
`.py` dan `.js` polos yang dimuat browser langsung. Pustaka browser sudah divendur
di `web/lib/`, dan tidak ada langkah build.

```bash
python -m venv .venv
.venv\Scripts\python.exe -m pip install "pip==24.0"                     # lihat catatan di requirements.txt
.venv\Scripts\python.exe -m pip install --index-url https://download.pytorch.org/whl/cpu torch==2.12.1 torchaudio==2.11.0
.venv\Scripts\python.exe -m pip install -r requirements.txt             # jalur LLM lokal + suara + mic + jendela
cp .env.example .env                    # sesuaikan konfigurasi jika diperlukan
.venv\Scripts\python.exe main.py        # satu-satunya perintah yang perlu dijalankan
```

Bawaannya dia muncul sebagai **Vtuber 2D di desktop**: jendela tanpa bingkai,
tembus pandang, tanpa entri taskbar, dan tanpa satu pun jendela konsol di
belakangnya. Dua jalan menyalakannya:

```
jalankan.pyw                                    # dua kali klik, nol jendela konsol
.venv\Scripts\python.exe main.py                # dari konsol
```

`jalankan.pyw` dijalankan `pythonw.exe` (interpreter yang sama, tanpa konsol) dan
tetap memakai `.venv`. Karena tidak ada konsol, jejak yang dulu cuma terbaca di sana
pindah ke berkas: `var/run.log` (boot, Vulkan, RVC) dan `var/pet.log` (jendela).
Alamat halamannya tetap `http://127.0.0.1:8787/` (port ikut `VTUBER_PORT` di `.env`),
dan **mode browser** tinggal `--browser` atau `VTUBER_TAMPAK=browser` — itu mode yang
dipakai untuk merapikan penampilannya.

## Mode browser

Dua kolom: kanvas karakter di kiri, panel di kanan. Panel berisi log percakapan,
kolom pesan, tombol mic, meter FPS, dan gugus tombol raut/pose/gerak — jadi semua
perkakas penyetelan ada di sini. Ini mode yang dipakai untuk merapikan tampilan.

## Mode pet

`VTUBER_TAMPAK=pet` (bawaan sejak 28 Sep) membuka jendela **tanpa bingkai, tembus
pandang, selalu di atas**, duduk di pojok kanan bawah area kerja — kakinya tepat di
garis taskbar. Dia bukan jendela biasa: `WS_EX_TOOLWINDOW` dipasang dan
`WS_EX_APPWINDOW` dibuang (hilang dari taskbar dan Alt+Tab), lalu
`SetLayeredWindowAttributes(..., LWA_COLORKEY)` membuat latar jendelanya tembus ke
desktop. Harga teknis color key yang perlu diketahui: tepi karakter yang
ber-antialias ikut sewarna latar setipis satu piksel — itu batas teknik, bukan
penyetelan yang salah.

| gestur / jalan | hasil |
|---|---|
| **klik kanan** pada dia | buka/tutup kotak chat + mic, kursor langsung di kolom ketik |
| **Ctrl+Shift+S** (hotkey global) | sama, dan bisa ditekan walau jendela lain sedang fokus |
| **Esc** atau klik di luar panel | tutup panel |
| seret tubuhnya | jendela ikut bergeser (`easy_drag`) |
| **ikon tray** | Tampilkan / Sembunyikan / Keluar |

Panel-nya berisi log, kolom pesan, tombol mic, dan satu baris status. Yang tetap
tersembunyi di mode pet hanya perkakas penyetel: meter FPS dan gugus raut/pose/gerak.
(Log dulu ikut hilang karena `#catatan` ber-class `gugus` dan aturan
`.gugus { display: none }` tidak pilih kasih — sekarang dikecualikan.)

### Sembunyi otomatis

`VTUBER_PET_SEMBUNYI` bawaannya **`layar-penuh`**: minggir hanya saat jendela depan
menutupi SELURUH monitor termasuk pita taskbar — video layar penuh dan game. Pilihan
lain: `tidak` (selalu tampil; berarti karakternya menutupi jendela kerja yang
dimaksimalkan) dan `maksimal` (juga saat jendela depan sekadar dimaksimalkan;
hindari kalau kerja sehari-hari memakai jendela maksimal — karakternya hampir selalu
sembunyi dan itu terasa seperti rusak).

Aturan ini kini menyala justru karena mode pet jadi bawaan dan dia selalu di atas.
Sembunyi otomatis yang keliru pernah membuat karakternya **hilang tanpa pesan**, jadi
ikon tray bukan hiasan selama aturan ini menyala — ia
satu-satunya jalan memanggilnya kembali. Menyembunyikan lewat tray juga tidak
langsung dibatalkan pengintai: kehendak manual menang sampai keadaan layar berubah.

### Tiga hal yang tidak kelihatan tapi menentukan

1. **`transparent=True` pywebview tidak cukup di Windows.** pywebview menyalakan
   `DefaultBackgroundColor = Transparent` pada WebView2-nya
   (`platforms/edgechromium.py:114`) tetapi tidak pernah menyentuh form WinForms
   induknya, dan seluruh paketnya tidak sekali pun memakai `TransparencyKey` atau
   `SetLayeredWindowAttributes`. Hasilnya, terukur: `exstyle 0x50008` (tanpa
   `WS_EX_LAYERED`) dan `PrintWindow` memulangkan 397.035 piksel (240,240,240)
   seragam — karakter di atas kotak abu-abu pekat. `jendela.tembuskan()` menutupnya
   dengan `WS_EX_LAYERED` + `LWA_COLORKEY` memakai warna `BackColor` form itu
   sendiri. Harganya: tepi berantialias bercampur warna latar, jadi ada rim tipis.
2. **Jendelanya dibuang dari taskbar** (`WS_EX_TOOLWINDOW`, `WS_EX_APPWINDOW`
   dilepas) — kalau tidak, ia terasa persis seperti jendela aplikasi biasa.
3. **Posisi dihitung ulang setelah prosesnya sadar-DPI.** Sebelum
   `webview.start()`, prosesnya masih DPI-unaware dan `SPI_GETWORKAREA` menjawab
   satuan virtual (1536x816 di layar 1920x1080 berskala 125%). Dipakai apa adanya,
   kaki karakter mendarat **204 px di atas taskbar**.

### "Tanpa jendela sama sekali" — sudah dicoba, tidak bisa di mesin ini

Menanam karakter ke lapisan desktop (di belakang ikon, gaya wallpaper hidup) diuji
27 Sep dan gagal; rinciannya di `RENCANA-DESKTOP.md` Fase 1. Ringkasnya: tidak ada
kanvas `WorkerW` di mesin ini (pesan `0x052C` dicoba dengan empat variasi parameter,
nihil), dan memaksa `SetParent` ke `Progman` membuat jendelanya runtuh jadi 0x0
serta permukaan WebView2-nya mati. Karena itu kesan "bukan jendela" dikejar lewat
perilaku — sembunyi otomatis, tray, dan hotkey — bukan lewat lapisan.

Dua fakta teknis yang perlu diketahui sebelum mengubah apa pun di sini:

1. **Jendela hidup di PROSES ANAK**, bukan di proses server. Dengan RVC (torch +
   fairseq + onnxruntime) termuat di proses yang sama, `webview.start()` kembali
   seketika tanpa satu baris galat pun: WinForms menuntut thread utama ber-apartment
   STA, dan COM sudah disetel lebih dulu oleh tumpukan audio. Terukur A/B -- tanpa
   RVC jendela muncul, dengan RVC hilang. Anaknya mengawasi PID induk
   (`GetExitCodeProcess`), jadi kalau server dibunuh paksa jendela menutup diri
   dalam ≤6 dtk (terbukti) dan tidak tertinggal sebagai kartu hantu.
2. **Live2D tetap dirender JS** di dalam WebView2. SDK Cubism tidak punya jalur
   Python, dan build Cubism Native butuh compiler C++ yang tidak ada di mesin ini.
   Jadi "tanpa JS" di mode pet berarti *Master tidak pernah membuka browser atau
   menyentuh berkasnya* -- bukan JS-nya hilang. `web/tampak.js` hanya menulis
   `html[data-tampak="pet"]`; halaman, kontrak DOM, dan seluruh modul JS-nya sama
   persis dengan mode browser, sengaja supaya tidak ada dua sumber kebenaran.

Transparansinya diukur, bukan dipercaya: dari 29.929 titik sampling di kawasan
jendela, hanya 1.351 yang berubah saat jendela ditampilkan -- dan kotak merah ujiannya
sendiri menyumbang 1.445. Artinya desktop tembus sepenuhnya.

Kalau `bin/llama/` kosong, `VTUBER_LLM_PROVIDER=vulkan` jatuh ke CPU dan **mengatakannya**
di baris banner -- lihat "GPU terintegrasi" sebelum menyalakan jalur itu. Tanpa
`pip install`, tidak ada engine yang bisa jalan: `/api/chat` membalas 503 dan `/api/tts`
menyerah dengan pesan jelas. **Tidak ada satu pun jalur yang jatuh ke cloud.**

## Aset

Proyek ini **tidak lagi membawa skrip pengunduh**. Semua aset di bawah sudah ada di
mesin ini dan di-`.gitignore` (lisensi Live2D melarang modelnya diedarkan sebagai
berkas lepas, dan yang lain terlalu besar untuk repo). Kalau pindah mesin atau
`.venv` dibuat ulang, aset-aset ini **disalin manual** -- tidak ada lagi tombolnya:

| Lokasi | Isi | Cara mendapatkannya dulu |
|---|---|---|
| `model/*.gguf` | Llama 3.2 3B Q4_K_M (2,02 GB) | GGUF Llama 3.2 dari HuggingFace |
| `aset/suara/piper/` | voice Indonesia `id_ID-news_tts-medium` (61 MB) | rilis Piper |
| `aset/suara/rvc/` | checkpoint Furina (v2, 40 kHz) | hasil latih di Applio |
| `aset/suara/model-dasar/` | HuBERT + rmvpe (±730 MB) | unduhan dasar `rvc_python` |
| `aset/suara/whisper/` | `base` (142 MB) / `small` (470 MB) | repo `Systran/faster-whisper-*` |
| `bin/llama/` | `llama-server.exe` + DLL Vulkan (92 MB) | build Windows resmi llama.cpp |
| `public/models/silverwolf/` | model karakter + 6 tekstur 8192 | berkas kerja karakter (`var/pasang_silverwolf.py`, tak ter-track) |
| `public/live2dcubismcore.min.js` | Cubism Core | SDK resmi Live2D |

Dua catatan yang masih benar: `base_model/` RVC hidup **di dalam**
`.venv/Lib/site-packages/rvc_python/`, jadi `.venv` baru berarti menyalin ulang
±730 MB itu ke sana. Dan `silverwolf.model3.json` + isi `ekspresi/` dibuat oleh
skrip pemasangan di `var/` — yang tidak ikut ke git, jadi salinan manual juga
berarti menyalin folder `public/models/silverwolf/` utuh.

## Arsitektur Full Offline

Yang dulu Node sekarang Python: satu proses `main.py` (Flask) menjalankan model lokal (Llama 3.2 GGUF via `llama-cpp-python`),
sintesis suara lokal (Piper + RVC Furina), menulis memori ke vault Obsidian, **dan** menyajikan halaman beserta
aset model. 100% offline tanpa dev server terpisah.

| Komponen | Dahulu (Node + Vite) | Sekarang (Python 100% Offline) |
|---|---|---|
| **Server & LLM** | `server/index.js` (Cloud Gemini API) | `main.py` (Flask) + `model_lokal.py` (CPU) / `model_vulkan.py` (GPU terintegrasi) |
| **Mic (STT)** | Web Speech API browser (cloud Google) | `web/mikrofon.js` rekam WAV -> `server_py/stt_whisper.py` (Whisper lokal) |
| **Penyaji Web** | `npm run dev` (Vite di :5173) | `server_py/statis.py` menyajikan `web/` dan `public/` |
| **Env Web** | `import.meta.env.VITE_*` | `window.__VTUBER_ENV__`, disuntikkan Python ke `index.html` |
| **Frontend** | `src/*.ts` + `tsconfig.json` | `web/*.js` — ESM asli browser tanpa build step |
| **Pustaka Web** | `node_modules` (270 MB) | `web/lib/` (572 KB: pixi + cubism4) |

## Model karakter

Karakternya **Silver Wolf**, model Live2D Cubism 4 dengan **358 parameter**
(didaftarkan di `silverwolf.cdi3.json`), **6 atlas tekstur** 8192, dan folder
kerja ber-nama Indonesia:

```
public/models/silverwolf/
  silverwolf.model3.json      FileReferences + Groups + daftar ekspresi & motion
  silverwolf.moc3             geometri yang sudah dikompilasi (jangan disunting)
  silverwolf.physics3.json    rambut, baju, perhiasan bergoyang
  silverwolf.cdi3.json        label parameter untuk editor
  tekstur/texture_00.png .. 05.png
  ekspresi/*.exp3.json        salinan untuk alat luar (VTube/Cubism); isinya
                              ditimpa resep .env saat runtime
  gerakan/berubah-1.motion3.json   (2,33 dtk)  ubah wujud
  gerakan/berubah-2.motion3.json   (2,33 dtk)  ubah wujud, varian
  gerakan/siklus.motion3.json      (1,67 dtk)  isyarat badan/gamepad
  gerakan/tidur.motion3.json       (4,00 dtk)  molor
```

**Letak dua daftar itu penting dan pernah salah.** `Expressions` dan `Motions`
harus berada **di dalam** `FileReferences`; pustaka membacanya sebagai
`t.FileReferences.Expressions` / `.Motions`. Ketika keduanya tertanam di level
teratas (bentuk yang dihasilkan pemasangan lama), pustaka tidak melihat apa pun dan
tidak mengeluh: `expressionManager` tidak pernah terbentuk — sembilan wajah mati
tanpa pesan — dan `motionManager.definitions` jadi `{}` sehingga keempat gerakan
tidak bisa dipanggil. `web/wajah.js:siapkanSettings()` sekarang menormalkan
letaknya sebelum model dimuat, jadi salinan lama pun tetap tampil benar.

Akting wajah model ini **bukan** lapisan `Param59` model lama, melainkan 17
sakelar artmesh `key1..key17` (grup `ParamGroup5` di cdi3 aslinya, rentang 0..1).
Namanya dari berkas asli `银狼.cdi3.json` — cdi3 hasil pemasangan di mesin ini
kehabisan label itu, jadi tabelnya ditulis di sini:

| Sakelar | Arti (nama aslinya) | Dipakai untuk |
|---|---|---|
| `key1` | 黑脸 wajah datar/gelap | belum terpakai |
| `key2` | 脸红爱心 pipi merah + hati | `[goda]` |
| `key3` | 生气 marah | `[sebal]` |
| `key4` | 晕 pusing | `[bingung]` |
| `key5` | `><` mata tertutup kencang | `[senyum]` |
| `key6` | `0.0` mata bulat kosong | `[kaget]` |
| `key7` | 星星眼 mata bintang | `[semangat]` |
| `key8` | 流泪 air mata | `[sedih]` |
| `key9` | 正常眼镜 kacamata | `[prop:kacamata]` |
| `key10` | 吹泡泡 meniup gelembung | `[lelah]` |
| `key11` | 变身 henshin | `[prop:ubah-wujud]` |
| `key12` | 水印 watermark | belum terpakai |
| `key13` | 外套 jaket | `[prop:jaket]` |
| `key14` | 抱胸手 tangan melipat dada | pose `tangan-1` |
| `key15` | 划卡手 tangan menggeser kartu | pose `tangan-4` |
| `key16` | 捧心手 tangan di dada | pose `tangan-2` |
| `key17` | 要饭手 tangan mengemis | pose `tangan-3` |

Model ini **tidak saling-mematikan** sakelarnya, jadi tiap resep di `.env` menulis
yang dia mau DAN memadamkan tetangga yang memakai artmesh sama (`key8=1 key2=0
key4=0 key7=0`). Kalau suatu resep lupa, wajahnya menumpuk dan hasil akhirnya
dijelaskan `web/konfigurasi.js:periksaTerhadapModel` di baris status halaman.
Gambar pedoman visual aslinya ikut terbawa di `var/silverwolf-mentah/银狼/`
(`按键设置说明.png`), tidak di-commit karena lisensi.

**Seberapa besar tiap resep benar-benar mengubah gambar** (terukur 28 Sep, Chromium
headless, dibaca dari opasitas 375 artmesh; lantai drift tanpa melakukan apa pun =
14 artmesh pada 0,005):

| Tag | Artmesh berubah | Opasitas terbesar |
|---|---|---|
| `[sebal]` | 51 | 1,0 |
| `[senyum]` / `[kaget]` | 36 | 1,0 |
| `[sedih]` | 24 | 1,0 |
| `[goda]` | 22 | 1,0 |
| `[semangat]` | 18 | 1,0 |
| `[bingung]` | 17 | 1,0 |
| `[lelah]` | 15 (= lantai + 1) | 1,0 |
| `[prop:kacamata]` | 14 | 0,80 |
| `[prop:jaket]` | 27 | 0,79 |
| `[prop:ubah-wujud]` | 60 | 0,78 |
| `[prop:tangan-1..4]` | 58 / 53 / 23 / 19 | ~0,79 |
| gerakan `siklus` | 25 | 0,91 |

Angka itu yang membuat `key9` perlu `:mati=0` dan bukan sekadar hiasan sintaks, dan
ia juga menunjukkan `[lelah]` paling halus di antara sembilan wajah: satu artmesh
(gelembung). Mau lebih kelihatan, cukup ganti barisnya di `.env` -- misalnya
`key1=1` (黑脸, wajah datar) yang sampai sekarang belum dipakai siapa-siapa.

Napas, goyang kepala, dan kedip tidak butuh berkas motion — pustaka
`pixi-live2d-display` sudah menyetelnya sendiri (`Groups.EyeBlink` menunjuk
`ParamEyeLOpen/ROpen`, `Groups.LipSync` menunjuk `ParamMouthOpenY`), dan itu alasan
`gerakan/` sengaja tidak dipasang sebagai grup Idle: kalau ada motion yang jalan,
pustaka justru mematikan kedip otomatisnya.

## Diatur lewat .env

Semua yang bergerak, berubah wajah, dan mengukur piksel dibaca dari satu berkas:
`.env` isinya, `web/konfigurasi.js` satu-satunya parsernya. Tidak ada halaman
penyetel kedua — `/perkakas.html` dibuang 28 Sep karena masih menunjuk jalur model
`penyihir` yang sudah tidak ada. Cara melihat apa yang benar-benar terpakai:

* baris **status** di mode browser: `siap — 9 wajah, 7 pose, 4 gerakan · ... · N
  konfigurasi perlu dicek` (angka itu dihitung dari nilai efektif, bukan dari harapan);
* `window.__vtuber` di devtools: `.konfig` (nilai efektif), `.ekspresiTerpasang`,
  `.peringatan`, `.gerakTersedia`, `.keadaan.status()`, `.setEkspresi('sebal')`,
  `.picuGerak('siklus', 3)`.

| Yang mau diubah | Kunci |
|---|---|
| Raut wajah (9) | `VITE_WAJAH_<NAMA>="key7=1 key2=0 key4=0 key8=0"` |
| Pose / aksesoris (7) | `VITE_POSE_<NAMA>="key13=1"`, tag `[prop:jaket]` dan `[prop:jaket=mati]` |
| Lepas semua aksesoris | tag `[prop:kosong]` |
| Wajah saat dibuka dan lama pudarnya | `VITE_EKSPRESI_DASAR`, `VITE_PUDAR_WAJAH_MS` |
| Gerakan (motion) | `VITE_GERAK_<NAMA>="grup=isyarat berkas=gerakan/siklus.motion3.json ulang=false"` |
| Isyarat sekali jalan dari balasan | tag `[gerak:siklus]`, `[gerak:kosong]` untuk menghentikan |
| Mesin keadaan (diam/bicara/tidur) | `VITE_KEADAAN`, `VITE_KEADAAN_GERAK_*`, `VITE_KEADAAN_JEDA_DETIK`, `VITE_KEADAAN_DETIK_TIDUR` |
| Ukuran kotak avatar (CSS px) | `VITE_PANGGUNG_UKURAN`, `VITE_PANGGUNG_LEBAR`, `VITE_PANGGUNG_TINGGI` |
| Seberapa besar karakter mengisi kotak | `VITE_AVATAR_ZOOM`, `VITE_AVATAR_X`, `VITE_AVATAR_JANGKAR` |
| Jumlah piksel nyata / ketajaman | `VITE_RENDER_SKALA`, `VITE_RENDER_SKALA_MAKS`, `VITE_RENDER_HALUS` |
| Kedip, napas, kepala ikut kursor | `VITE_KEDIP`, `VITE_NAPAS`, `VITE_IKUTI_KURSOR` |
| Atlas tekstur yang dipasang | `VITE_TEKSTUR` (model ini sudah 8192, maksimum dari aslinya) |
| Berapa lama dia boleh menggambar (hemat GPU) | `VITE_IRAMA_JEDA_SAAT_SEMBUNYI`, `VITE_IRAMA_FPS_SAAT_TAK_FOKUS` |

Satu sintaks untuk semuanya: token `Id=Nilai` dipisah spasi; blend default `Add`
menambah di atas nilai bawaan parameter, `:Overwrite` menulis mentah, `:Multiply`
mengali; `kosong` berarti tanpa parameter. Nama kunci diterjemahkan apa adanya —
`VITE_POSE_TANGAN_1` menjadi pose `tangan-1`. Id yang tidak ada di model, nilai yang
keluar rentang, dan tabrakan tulisan antara wajah dan pose dilaporkan di baris status
halaman ("N konfigurasi perlu dicek") dan di log browser. Ubah nilainya cukup muat
ulang jendela.

Wajah memakai sistem ekspresi pustaka (satu wajah pada satu waktu), sedangkan pose
ditulis sebagai lapisan parameter paling akhir setiap frame — sehingga kacamata,
jaket, atau satu posisi tangan tetap menempel walau wajahnya sedang sedih.

### Mesin keadaan: dia tidak lagi patung

Empat motion yang ada sebelumnya cuma bisa dipanggil dari tombol — dan tombol itu
disembunyikan di mode pet. `web/keadaan.js` memakainya sendiri lewat tiga keadaan:

| Keadaan | Kapan | Yang dilakukan |
|---|---|---|
| `bicara` | suara mulai berbunyi | satu isyarat opsional (`VITE_KEADAAN_GERAK_BICARA`, bawaan `kosong`) — kecuali balasannya sudah membawa `[gerak:]` sendiri |
| `diam` | tidak ada suara dan tidak ada aktivitas | isyarat badan tiap `VITE_KEADAAN_JEDA_DETIK` (dikalikan acak 0,5–1,5x supaya tidak seperti metronom), prioritas IDLE: hanya kalau benar-benar kosong |
| `tidur` | `VITE_KEADAAN_DETIK_TIDUR` tanpa suara, klik, atau ketikan | `gerakan/tidur.motion3.json` dengan `ulang=true`, berhenti saat ada aktivitas |

Dua keputusan yang sengaja:

* **Waktunya dihitung dari frame yang digambar, bukan jam dinding.** Saat jendela
  tersembunyi `web/iriama.js` menghentikan ticker; dengan jam dinding dia akan
  langsung "tidur" pada frame pertama setelah dipanggil kembali — padahal itu justru
  momen dia seharusnya bangun.
* **Tidak ada motion "ngobrol" di model ini, jadi `bicara` bukan animasi bicara.**
  Rahang tetap dibaca dari amplitudo audio (`web/suara.js` + `ParamMouthOpenY`), dan
  menambah isyarat badan di awal balasan hanya menghias — itu pun bawaannya mati.

Prioritas motion memakai enum pustaka: `NONE=0` (ditolak), `IDLE=1` (hanya saat
kosong), `NORMAL=2` (menyela ambient), `FORCE=3` (klik dan tag, wajib jalan).
Setelah motion sekali-jalan selesai, semua parameter ditulis ulang ke nilai bawaan;
tanpa itu tangan atau air mata membeku di posisi terakhir selamanya.

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

Rel kiri adalah dia; rel kanan adalah buku catatannya. Silver Wolf bekerja sendirian
di base camp-nya dan mencatat apa yang dia temukan, dan memori build ini pun
sungguh-sungguh berupa catatan Markdown di vault — jadi panelnya sebuah ledger
lapangan, bukan dashboard.

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
papan ketik ---------------> teks --> Llama 3.2 3B GGUF --> teks + [tag]
                                       (CPU / Vulkan GPU)        |
mic --> WAV 16 kHz --> /api/stt --> Whisper base --> teks         |
           (lokal, di mesin ini)                                  |
                                                            ekspresi Live2D
                     /api/tts --> jalur_suara (pekerja tunggal + cache)
                          piper     --> WAV 22,05 kHz  (offline, CPU)
                          piper+rvc --> RVC/Furina --> WAV 40 kHz
                                          |
                             AnalyserNode (RMS) -> ParamMouthOpenY
```

- **`main.py`** — satu proses untuk semuanya (Flask): LLM lokal (`model_lokal` / `model_vulkan`), TTS lokal (`jalur_suara`),
  memori Obsidian (`vault`), dan sajian halaman (`statis`).
- **`server_py/model_lokal.py`** — streaming inferensi LLM offline menggunakan `llama-cpp-python` membaca GGUF di `model/`.
- **`server_py/model_vulkan.py`** — penyedia chat di GPU terintegrasi: menyalakan
  `bin/llama/llama-server.exe` sebagai **proses anak** (port acak, hanya 127.0.0.1,
  API key acak per boot), streaming dari `/v1/chat/completions`, dan menyapu sisa
  proses lama saat boot. Bentuk keluarannya sama dengan `model_lokal.alir()`, jadi
  sisi streaming `main.py` tidak perlu tahu mana yang menjawab.
- **`server_py/stt_whisper.py`** — mic jadi teks: WAV dari browser -> `wave` (stdlib)
  -> numpy -> faster-whisper (CTranslate2, CPU, `int8`). Model dibuka dari folder
  dengan jalur lengkap, tanpa `download_root`, tanpa HuggingFace hub.
- **`server_py/statis.py`** — pengganti dev server: menyajikan `web/` dan `public/`, MIME presisi, dan perlindungan path traversal.
- **`server_py/jalur_suara.py`** — orkestrator suara: satu thread pekerja + antrean berbatas, cache per kalimat, dedupe pekerjaan identik, dan fallback antar-resep saat satu engine melewati batas waktu.
- **`server_py/tts_piper.py`** / **`tts_rvc.py`** — engine TTS lokal: Piper ONNX dan RVC Voice Conversion Furina.
- **`server_py/wav.py`** — bungkusan dan pembaca header WAV.
- **`persona.md`** — sifat dan gaya bicara karakter. Ini konfigurasi, bukan model yang
  dilatih: diedit langsung, dan selalu dikirim sebagai system instruction.
- **`web/konfigurasi.js`** — satu-satunya parser `.env` (wajah, pose, gerakan, keadaan,
  ukuran), plus `periksaTerhadapModel()` yang menguji resep terhadap tabel parameter
  model yang sedang berjalan. Bawaannya ada di berkas ini, `.env` menimpanya.
- **`web/wajah.js`** — `siapkanSettings()` menormalkan letak `Motions`/`Expressions`
  di `model3.json` sebelum pustaka membacanya; `suntikEkspresi()` menyuntik resep
  `.env` ke expression manager saat runtime; `LapisanPose` menjaga pose tetap di atas
  wajah (`beforeModelUpdate`).
- **`web/ekspresi.js`** — gerbang tag: nama wajah, pose, dan gerakan diambil dari
  konfigurasi (bukan ditulis di sini), kanal `[prop:...]` dan `[gerak:...]` dikenali,
  dan tag itu dikupas dari layar saat teks masih mengalir.
- **`web/keadaan.js`** — mesin `diam`/`bicara`/`tidur`: memilih motion dari yang
  terdaftar, memanggilnya dengan prioritas yang benar, dan bangun saat ada aktivitas.
- **`web/main.js`** — kanvas + resolusi (ikut `devicePixelRatio` terus-menerus), tombol
  panel dari `.env`, `picuGerak()` dengan prioritas, dan gerakan ulang parameter ke
  bawaan setelah motion sekali-jalan selesai.
- **`web/mikrofon.js`** — tombol mic di halaman chat. **Tidak ada lagi Web Speech API**:
  browser merekam lewat `getUserMedia` + `ScriptProcessor`, memotong pada jeda diam
  (ambang RMS 0,012, sama dengan lantai noise lip-sync), membungkus WAV 16 kHz mono,
  dan mengirimnya ke `/api/stt`. Semuanya terjadi di dalam mesin.
- **`web/suara.js`** — memutar WAV dan mengukur amplitudo per frame; keadaan suaranya
  (`berbicara`/`diam`) bisa didaftarkan banyak pemakai — chat untuk lampu indikator,
  `keadaan.js` untuk mesin gerak.
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

## Suara lokal: performa & benchmark offline

Angka di bawah **terukur di mesin ini** pada 26 Sep (rantai penuh, 8 kalimat, dua f0).
Mesin uji: i5-1135G7 (4 core/8 thread), Intel Iris Xe, 16 GB RAM, **tanpa GPU NVIDIA**.

| Jalur / Engine | Median per kalimat | p95 | RTF | Puncak RAM | Keterangan |
|---|---|---|---|---|---|
| `piper` saja | **0,29 – 0,53 dtk** | 0,61 dtk | **0,12 – 0,19** | ±200 MB | Sangat cepat, real-time |
| `piper+rvc` f0 `pm` | 7,36 dtk | 9,93 dtk | 1,47 | 2160 MB | Default cepat CPU |
| `piper+rvc` f0 `rmvpe` | 8,04 dtk | 14,70 dtk | 1,80 | 2678 MB | Nada lebih halus |

Kesimpulan performa:
- **Piper TTS** menghasilkan audio dalam pecahan detik (<0.5s), sangat efisien di CPU.
- **RVC** memberikan pewarnaan suara Furina yang khas.
- **Cache suara otomatis** instan (<5ms) untuk kalimat yang pernah disintesis sebelumnya.
- Rantainya dipilih lewat `.env`: `VTUBER_TTS_RANTAI=piper+rvc,piper`. Jika RVC sibuk atau melewati batas detik, sistem otomatis fallback ke Piper murni.

Cara memasang: lihat tabel **Aset** -- semuanya disalin manual ke tempatnya.

`--model-dasar` perlu dijalankan ulang setiap kali `.venv` dibuat ulang: `rvc_python`
membaca `base_model/` dari dalam direktori paketnya sendiri, bukan dari proyek.

Bukti sisi browser, dijalankan 2026-09-26 pada Chromium headed (Playwright global,
bukan bagian proyek -- Node sudah tidak dipakai di sini): `POST /api/tts` membalas
`200 audio/wav` dengan `x-tts-model: piper`, `decodeAudioData` menerima berkasnya
(1,07 dtk), RMS pada `AnalyserNode` menyentuh **0,25**, dan `window.__vtuber.mulut`
bernilai **0,681** setelah `antre()` selesai. Artinya rahang benar-benar digerakkan
audio Piper, bukan hanya "file-nya valid".

Catatan metode: pemeriksaan pertama melaporkan "rahang diam" dan itu **salah tes,
salah produk** -- `antre()` tidak di-await sehingga sampel diambil sebelum konteks
audio bangun. Kalau suatu hari tes rahang melaporkan nol, curigai dulu caranya
sebelum menyalakan kodenya.

Cara memilih suara dengan telinga (angka tidak bisa mengganti ini):

```bash
.venv\Scripts\python.exe scripts/adu_suara.py --transpose 0,12
```

Rantainya dipilih lewat `.env`, tanpa menyentuh kode: `piper` dan `piper+rvc` bisa ditumpuk dengan koma, mana yang gagal dilompati. Tiga perilaku
yang membuat penumpukan itu benar-benar terpakai, bukan sekadar tertulis:

- **Hasil yang telat tetap masuk cache.** Yang menulis cache adalah pekerjanya,
  bukan penunggunya. Tanpa ini, tiap kalimat RVC yang melewati `VTUBER_TTS_BATAS_DETIK`
  dibuang hasilnya dan kalimat yang sama miss selamanya.
- **Resep yang terbukti tidak selesai diistirahatkan** selama
  `VTUBER_TTS_JEDA_RESEP` (bawaan 60 dtk). Tanpa jeda itu, kalimat ke-2..N dari satu
  jawaban panjang membayar ulang 20 dtk kegagalan yang sama -- dan yang habis bukan
  kuota, tapi CPU mesin ini sendiri.
- **Pekerja membuang pekerjaan yang tidak ada penunggunya lagi**, dan `var/tmp-suara`
  disapu saat boot. Dua berkas `_masuk.wav` tertinggal dari proses yang dipotong di
  tengah konversi -- `finally` tidak jalan kalau prosesnya dibunuh.

Satu hal yang harus diketahui soal `piper+rvc`: voice Piper Indonesia adalah **suara berita
laki-laki berlogat asing** (MODEL CARD-nya: 1 penutur, medium, hasil fine-tune dari
suara Inggris), jadi RVC harus menjembatani gender, bukan sekadar warna — dan hasil
eksperimennya ada di halaman yang dicetak `adu_suara.py`.

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

Mode per kalimat itu menambah satu panggilan TTS per kalimat. Biayanya nyata di CPU
ini (Piper 0,3-0,5 dtk, `piper+rvc` 7-15 dtk per kalimat), jadi matikan dengan
`VTUBER_TTS_PER_KALIMAT=false` kalau suara mulai tertinggal dari teks. Jeda sebelum
token pertama bukan lagi antrean di sisi Google seperti dulu: itu prompt-processing
Llama 3.2 di mesin ini sendiri, dan dua perbaikan yang benar-benar terbukti ada di
bagian "GPU terintegrasi" — memindahkan hitungan ke Iris Xe (110 -> 171 tok/dtk) dan
menyimpan persona di prompt cache (4,6 dtk -> 0,4 dtk pada slot hangat).

## GPU terintegrasi: apa yang benar-benar bisa dipindahkan

Mesin ukur: i5-1135G7 + **Intel Iris Xe**, 16 GB RAM, tanpa GPU diskret, driver
32.0.101.7088, Vulkan 1.4.

Yang harus diterima lebih dulu: **Iris Xe tidak punya VRAM sendiri.** Angka
"Shared GPU memory 7,9 GB" di Task Manager dipinjam dari 16 GB RAM yang sama dengan
yang dipakai model. Jadi memindahkan kerja ke GPU di sini menambah **daya hitung**,
bukan menambah memori — dan kalau yang habis adalah RAM, GPU tidak menolong.

`llama-bench` resmi, Llama 3.2 3B Q4_K_M, prompt 2048 token + generate 128 token,
3 pengulangan, flash attention menyala:

| penempatan lapis | baca prompt (tok/dtk) | keluar token (tok/dtk) |
|---|---|---|
| `-ngl 0` (CPU murni) | 109,7 ± 10,4 | 5,05 ± 1,11 |
| `-ngl 99` (Vulkan penuh) | **171,1 ± 8,0** | **9,91 ± 0,11** |

Dua hal yang tidak terlihat dari satu angka:

1. **`-fa on` adalah syarat, bukan hiasan.** Pengukuran pertama tanpa flash attention
   justru membalik keadaannya (GPU 6,8 vs CPU 8,6 tok/dtk) dan hampir membuat jalur
   ini dibuang. Dengan flash attention menyala, GPU menang di kedua kolom — dan
   keluar token jauh lebih **stabil** (±0,11 vs ±1,11), yang terasa sebagai suara yang
   tidak tersendat.
2. **Lebih sedikit lapis GPU bukan kompromi yang aman.** Sapuan `-ngl 0,8,16,24,99`
   memberi 138 / 141 / 156 / 163 / 166 tok/dtk untuk prompt, tapi keluar token di
   `-ngl 16` jatuh ke 6,9. Campuran CPU+GPU membayar sinkronisasi di tiap batas lapis.

Terukur di aplikasi nyata (`/api/chat`, satu proses `main.py`): byte pertama **4,6 dtk**
pada giliran pertama, lalu **0,4 dtk** saat slotnya masih hangat (`--cache-idle-slots`
menyimpan persona panjang di prompt cache, jadi tidak dihitung ulang tiap giliran).

**Yang TIDAK bisa dan tidak akan pernah bisa pindah ke GPU di proyek ini:** RVC.
Konversinya PyTorch, dan `torch-directml` tidak punya wheel untuk kombinasi
torch 2.12 + Python 3.10 di mesin ini (dicek langsung: `No matching distribution
found`). Jadi `piper+rvc` tetap CPU 7-15 dtk per kalimat, dan itu batas mesin, bukan
kelalaian konfigurasi. Piper juga sengaja dibiarkan di CPU: 0,3-0,5 dtk per kalimat
sudah cukup cepat, dan menggantinya berarti menukar `onnxruntime` yang sekarang
memegang seluruh jalur suara.

## Mic lokal: angka dan buktinya

`whisper/base` int8, 2 thread CPU, ucapan 7,8 detik hasil Piper:

| keadaan | waktu |
|---|---|
| panggilan pertama (model baru dimuat) | 1,5 dtk |
| panggilan berikutnya | **0,77 dtk** |
| hasil salin | `Apa yang bisa saya bantu hari ini?` |

`small` (470 MB) tersedia lewat `VTUBER_STT_MODEL=small` kalau akurasi `base` kurang;
di CPU ini `medium` tidak dicoba karena RAM kosong tinggal ±4,5 GB saat browser dan
llama-server sudah hidup.

Jalur utuhnya dibuktikan di browser nyata, bukan hanya di ujung server: Chromium
dengan mikrofon palsu (`--use-fake-file-for-audio-capture`) berisi WAV Piper, klik
tombol mic, dan hasilnya masuk ke log chat lalu dijawab Silver Wolf. Satu catatan
untuk yang menulis ulang tes ini: Chrome **tidak** mengalirkan audio file-palsu pada
sesi `getUserMedia` pertama (terukur: 0 blok audio), jadi tes perlu membuka perangkat
sekali sebagai pemanasan sebelum klik. Itu kelakuan alat uji, bukan produk.

## Memeriksa avatar tanpa menyentuh desktop

Suiter tes Python sudah dibuang 27 Sep dan tidak dikembalikan. Yang tinggal adalah
permukaan debug yang memang sudah ada di halaman: `window.__vtuber`
(`web/main.js`). Dari devtools — atau dari Chromium headless lewat `evaluate_js` —
empat pertanyaan penting bisa dijawab tanpa melihat layar:

| Yang ingin dipastikan | Coba |
|---|---|
| Resep wajah/pose benar-benar terpasang | `__vtuber.ekspresiTerpasang.length` (bawaan: 16 = 9 wajah + 7 pose) dan `__vtuber.peringatan` harus `[]` |
| Gerakan bisa dipanggil sama sekali | `__vtuber.gerakTersedia` (4 nama) lalu `await __vtuber.picuGerak('siklus', 3)` → `true` |
| Wajah benar-benar mengubah gambar | baca `internalModel.coreModel.getDrawableOpacity(i)` sebelum/sesudah `setEkspresi('sebal')`; lihat tabel terukur di bagian **Model karakter** |
| Mesin keadaan hidup | `__vtuber.keadaan.status()` → `{nama, sejakSah, sejakAktifSah, gerak}` |

Yang TIDAK bisa dibuktikan lewat angka: apakah gerakannya enak dilihat, dan apakah
rim color-key di tepi antialias masih mengganggu. Dua-duanya butuh mata Master.

## Perkakas & Pengelolaan

```bash
.venv\Scripts\python.exe scripts/adu_suara.py   # render sampel suara untuk dipilih dengan telinga
```

Satu-satunya perkakas yang tersisa di `scripts/` itu membaca `.env` lewat
`server_py/konfig.py` yang sama dengan server, dan `update_waifu_memory.py`
(penjaga pulau memori karakter -- bukan perkakas teknis).

Yang **tidak ada lagi**: pengunduh aset (`unduh_*`, `sedia_*`) dan seluruh suiter
tes (`uji_jalan`, `uji_suara`, `uji_kontrak` + `kontrak.json`). Itu pilihan pada
27 Sep, dan konsekuensinya perlu disebut jujur: tidak ada lagi yang otomatis
menangkap kalau suatu hari ada kode yang diam-diam memanggil cloud, dan tidak ada
lagi yang membuktikan kontrak HTTP `/api/*` tidak berubah bentuk. Yang masih
menjaga adalah baris banner saat boot (ia menyebut engine yang benar-benar hidup
atau mengakuinya mati) dan pesan 503 dari tiap endpoint.

`public/vad` (6,2 MB) dan `public/ort` (83 MB) **sudah dilepas 28 Sep**: nol
referensi di `web/*.js` (dibuktikan dengan grep), dan `web/mikrofon.js:13-16` memang
menyebutnya sengaja tidak dipakai karena bundelnya UMD, bukan ESM. Karena keduanya
di-`.gitignore` dan skrip pengunduhnya sudah dibuang, salinannya dititipkan di
`C:\Sampah Karantina\AI VTUBER\` dengan jalur pemulihan tercatat di `PULIHKAN.csv` —
bukan dihapus diam-diam. Yang ikut pindah: `web/lib/vad.bundle.min.js`,
`web/perkakas.html` (masih menunjuk jalur model lama), dan `scripts/probe_*.py`
(sekali pakai, 27 Sep). `jalankan.bat` menyusul digantikan `jalankan.pyw`, tapi itu
satu masih ada di riwayat git.

## Kredit

Aset dan pustaka pihak ketiga yang dipakai proyek ini, beserta pemiliknya:

- **Model karakter "Silver Wolf"** (`public/models/silverwolf`) — model Cubism 4
  berlisensi *Cubism SDK License*, berkas aslinya dari `var/silverwolf-mentah/银狼/`;
  nama berkas, folder, dan konfigurasinya dialihbahasakan ke Indonesia. Tidak
  di-commit (lisensi Live2D melarang model diedarkan sebagai berkas lepas).
- **Live2D Cubism Core for Web** (`live2dcubismcore.min.js`) — SDK resmi
  [Live2D Inc.](https://www.live2d.com/en/sdk/download/web/), *Cubism SDK License*.
- **[pixi-live2d-display](https://github.com/guansss/pixi-live2d-display)**
  oleh guansss — MIT.
- **[PixiJS](https://github.com/pixijs/pixijs)** — MIT. Renderer WebGL.
- **[llama.cpp](https://github.com/ggml-org/llama.cpp)** oleh ggml-org — MIT.
  `llama-server` + backend Vulkan yang menghitung Llama 3.2 di Iris Xe; biner
  Windows resminya disalin sekali ke `bin/llama/` (versi dipaku
  `b11206`, karena angka 171 tok/dtk adalah angka build itu).
- **[faster-whisper](https://github.com/SYSTRAN/faster-whisper)** oleh SYSTRAN — MIT,
  di atas **[CTranslate2](https://github.com/OpenNMT/CTranslate2)** (MIT).
- **[Whisper](https://github.com/openai/whisper)** oleh Open — MIT. Model `base`/`small`
  bahasa Indonesia yang menyalin mic di mesin ini.
- **[Piper](https://github.com/rhasspy/piper)** — MIT. TTS Indonesia (voice
  `id_ID-news_tts-medium`, satu penutur, kualitas medium).
- **[RVC](https://github.com/RVC-Project/Retrieval-based-Voice-Conversion-WebUI)** via
  fork `rvc_python` — MIT. Konversi warna suara ke Furina.
- **[vad-web](https://github.com/ricky0123/vad)** oleh ricky0123 — MIT,
  **[Silero VAD](https://github.com/snakers4/silero-vad)** — MIT, dan
  **[ONNX Runtime Web](https://github.com/microsoft/onnxruntime)** — MIT. Ketiganya
  pernah ikut terbawa ke `public/` tetapi **tidak pernah tersambung**: mic memakai
  ambang RMS sendiri di `web/mikrofon.js`. Asetnya sudah dilepas 28 Sep (lihat
  **Perkakas & Pengelolaan** di atas), jadi tidak ada lagi yang perlu dikredit di
  dalam repo ini selain catatan historis ini.

Sistem berjalan 100% offline: chat, suara, dan mic dihitung di CPU/GPU lokal tanpa
satu pun panggilan cloud. Vite,
TypeScript, dan `@google/genai` dipakai pada fase awal dan sudah dihapus bersama
`node_modules`; Web Speech API (mic ke server Google) menyusul pada 27 Sep.

Kode di repositori ini adalah karya proyek; seluruh aset dan pustaka di atas
tetap pada lisensinya masing-masing.

## Lisensi

Kode sumber proyek ini bebas dipakai sesuai ketentuan yang berlaku padanya.
**Model Live2D dan Cubism Core tidak termasuk** dan tidak diizinkan untuk
diredistribusi sebagai berkas lepas — karena itu keduanya dikecualikan dari
repositori (lihat tabel **Aset**). Cubism Core diambil dari situs resmi Live2D.
Untuk karakter publik, gunakan model milik sendiri.
