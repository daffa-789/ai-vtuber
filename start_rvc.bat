@echo off
setlocal
REM ==========================================================================
REM  HuoHuo - Layanan konversi suara RVC (timbre HuoHuo)
REM  Jalan di http://127.0.0.1:8081  (dipakai huohuo.config.rvc_service_url)
REM  Pakai environment TERPISAH: rvc-env (Python 3.10 + fairseq + rvc-python).
REM
REM  Layanan ini MEMBACA .env di akar repo sendiri, jadi semua parameter suara
REM  (VTUBER_RVC_TRANSPOSE, VTUBER_RVC_PROTEKSI, VTUBER_RVC_EQ*, dll) diubah di
REM  .env -- lalu restart berkas ini.
REM
REM  Soal RAM: layanan menahan ~2,5 GB saat aktif. Melepas model dari DALAM
REM  proses terbukti tidak mengembalikan memori (gc + trim hanya 0,06 GB), jadi
REM  ia MENGUNDURKAN DIRI -- prosesnya keluar -- setelah menganggur
REM  VTUBER_RVC_IDLE_HAPUS detik (bawaan 180; 0 = jangan pernah berhenti).
REM  Tidak perlu menyalakannya lagi dengan tangan: RVCAdapter di aplikasi
REM  menyalakan ulang layanan ini begitu butuh. Set VTUBER_RVC_AUTO_MULAI=tidak
REM  kalau kamu lebih suka mengendalikan proses ini sepenuhnya.
REM
REM  NOTE: butuh llama-server (otak) + Piper sudah aktif untuk suara penuh.
REM ==========================================================================

set "BASE=%~dp0"
set "PY=%BASE%rvc-env\Scripts\python.exe"
set "SVC=%BASE%rvc\rvc_service.py"

if not exist "%PY%" (
    echo [RVC] GAK KETEMU rvc-env di %PY%
    echo        Buat dulu: uv venv rvc-env --python 3.10 lalu pasang deps RVC.
    pause
    exit /b 1
)

echo [RVC] Menyalakan layanan suara HuoHuo di http://127.0.0.1:8081 ...
echo        Model dimuat saat kalimat pertama. Cek http://127.0.0.1:8081/status
echo        untuk melihat apakah model sudah terpasang. Tutup jendela untuk mati.
echo.

"%PY%" "%SVC%"

endlocal
