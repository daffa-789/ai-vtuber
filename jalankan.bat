@echo off
cd /d "%~dp0"
echo Menjalankan AI VTuber...
echo Buka browser di: http://127.0.0.1:8787/
echo Tekan Ctrl+C di jendela ini jika ingin menghentikan.
echo.
.venv\Scripts\python.exe server_py\app.py
pause
