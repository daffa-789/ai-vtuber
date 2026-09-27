@echo off
cd /d "%~dp0"
echo Menghidupkan Elaina...
echo.
echo Klik kanan pada dia untuk memunculkan kotak chat + mic.
echo Tekan Ctrl+C di jendela ini jika ingin menghentikan.
echo (Mau lewat browser? jalankan: .venv\Scripts\python.exe main.py --browser)
echo.
.venv\Scripts\python.exe main.py
pause
