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
REM  Soal RAM: model makan ~2,4 GB. Secara bawaan ia dimuat malas dan DIBONGKAR
REM  lagi setelah menganggur 180 detik (VTUBER_RVC_IDLE_HAPUS), supaya RAM
REM  kembali ke sistem saat tidak ngobrol. Set VTUBER_RVC_IDLE_HAPUS=0 untuk
REM  menahan model terus seperti dulu.
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
