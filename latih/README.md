# Pintu latihan

**Belum ada apa-apa yang dilatih.** Berkas ini ditulis supaya yang nanti melatih
tidak perlu merombak jalur suara yang sudah jalan. Keputusan 2026-09-25:
inference dulu, training belakangan — dan "belakangan" itu baru bisa dimulai
kalau ada korpus, yang **sampai hari ini tidak ada di disk mana pun**.

Satu batas yang membentuk seluruh rencana di bawah: **Master tidak mau merekam
suaranya sendiri.** Jadi tidak ada satu pun jalur di sini yang bergantung pada
tombol rekam.

## Mesin ini tidak untuk melatih

i5-1135G7, Intel Iris Xe, tanpa NVIDIA. Melatih RVC di sini tidak selesai.
Latih sekali-jalan di **Colab atau Kaggle (T4 gratis)**, bawa pulang hasilnya.
Proyek ini hanya jadi tempat Menjalankan.

Jangan melatih di `.venv` proyek: `rvc_python` memanggil `use_fp32_config()` saat
impor di jalur non-CUDA, yang menulis ulang berkas `configs/*.json` dan
`modules/train/preprocess.py` **di dalam site-packages**. Untuk inference itu benar;
untuk training itu salah dan sulit dilacak.

## Jalur A — model RVC baru (warna suara)

Ini yang paling murah hasilnya, dan **tidak perlu mengubah satu baris kode pun**.

1. Kumpulkan audio vokal bersih 10–30 menit (satu penutur, tanpa musik/Reverb).
   Bukan suara Master — rekaman publik karakter, atau keluaran TTS yang sudah
   ada di proyek ini (lihat Catatan di bawah).
2. Slice jadi potongan 3–10 detik, mono, 16 kHz → taruh di
   `latih/data/mentah/<nama>/`.
3. Latih di Colab/Kaggle dengan Applio (salinan lengkap sudah ada di
   `E:\ApplioV3.6.5`, Py 3.12 — dipakai di mesin sewaan, bukan di sini).
4. Ambil `<nama>.e<epoch>_s<step>.pth` (dan `added_*.index` kalau dibuat) →
   salin ke **`aset/suara/rvc/<nama>/`**.
5. Ganti satu baris: `VTUBER_RVC_MODEL=<nama>` di `.env`.

`rvc_python` memindai `models_dir/*/` sendiri, jadi nama folder = nama model.
Folder `aset/suara/` sudah di-`.gitignore`, jadi tidak ada yang bocor ke repo.

## Jalur B — suara Piper sendiri (bukan cuma warna, tapi lafal & iramanya)

`pip install "piper-tts[train]"` lalu ikuti `docs/TRAINING.md` milik paketnya
(notebook `train_*.ipynb`, ada jalur Colab). Butuh korpus bahasa Indonesia yang
lebih bersih dan lebih panjang daripada jalur A. Hasilnya satu `.onnx` + `.onnx.json`
→ taruh di `aset/suara/piper/` → `VTUBER_TTS_PIPER_MODEL` menunjuk ke sana.

## Dari mana korpusnya kalau tidak rekaman

Rantai yang sekarang jalan (TTS → WAV) menghasilkan audio karakter **kapan saja,
tanpa rekaman**. Itu bahan mentah yang sah untuk Jalur A — bukan untuk Jalur B,
karena training Piper mengharapkan suara manusia asli. Kalau suatu hari tujuan
"yang ditrain" jadi penting, mulailah dari sana, bukan dari mikrofon.

## Struktur folder ini

```
latih/data/mentah/<nama>/     audio sumber apa adanya        (kosong)
latih/data/laras/16k/<nama>/  keluaran pemotongan 16 kHz     (kosong)
latih/data/daftar/<nama>.list konvensi daftar Applio         (kosong)
```

Pemotong audionya nanti `latih/potong.py` (±40 baris, memakai
`rvc_python.lib.slicer2.Slicer` yang sudah terinstal + `soundfile` mono 16 kHz).
**Sengaja belum ditulis:** tidak ada korpus yang mau dipotong, dan skrip yang
tidak ada pemanggilnya cuma jadi tempat asumsi salah. Kalau memang perlu, ia
skrip mandiri — tidak boleh dipanggil dari server.
