@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ============================================
echo  KunefeLauncher SETUP olusturuluyor
echo ============================================

set "PY="
call :findpython
if defined PY goto havepython

echo.
echo Python bulunamadi, indirilip kuruluyor (2-3 dakika)...
set "PYDL=%TEMP%\python_installer.exe"
if exist "%PYDL%" del "%PYDL%" >nul 2>&1
powershell -NoProfile -ExecutionPolicy Bypass -Command "[Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12; $ProgressPreference='SilentlyContinue'; Invoke-WebRequest -UseBasicParsing -Uri 'https://www.python.org/ftp/python/3.12.10/python-3.12.10-amd64.exe' -OutFile '%PYDL%'"
set "SZ=0"
if exist "%PYDL%" for %%A in ("%PYDL%") do set "SZ=%%~zA"
if %SZ% LSS 20000000 goto nopython
echo Python kuruluyor...
start "" /wait "%PYDL%" /quiet InstallAllUsers=0 PrependPath=1 Include_launcher=0 Include_test=0 Include_doc=0 Shortcuts=0
del "%PYDL%" >nul 2>&1
call :findpython
if not defined PY goto nopython

:havepython
echo Python: %PY%
"%PY%" -m pip install --upgrade pip
"%PY%" -m pip install minecraft-launcher-lib pillow certifi pyinstaller
if errorlevel 1 goto fail

if exist dist rmdir /s /q dist
if exist output rmdir /s /q output
if exist payload rmdir /s /q payload
mkdir payload

echo.

echo.
echo [1/2] Launcher EXE derleniyor...
"%PY%" -m PyInstaller --noconfirm --clean --onedir --windowed --name KunefeLauncher --icon "assets\icon.ico" --add-data "assets\logo.png;assets" --add-data "assets\hero.jpg;assets" --add-data "assets\packs;assets\packs" --add-data "assets\extra_mods;assets\extra_mods" --exclude-module numpy --exclude-module matplotlib --exclude-module pandas KunefeLauncher.py
if errorlevel 1 goto fail
if not exist "dist\KunefeLauncher\KunefeLauncher.exe" goto fail
"%PY%" -c "import shutil; shutil.make_archive('payload/app','zip','dist/KunefeLauncher')"
if errorlevel 1 goto fail

echo.
echo [2/2] Setup olusturuluyor...
"%PY%" -m PyInstaller --noconfirm --clean --onefile --windowed --name KunefeLauncher_Setup --icon "assets\icon.ico" --add-data "payload\app.zip;payload" --add-data "assets\logo.png;assets" --distpath output setup.py
if errorlevel 1 goto fail
if not exist "output\KunefeLauncher_Setup.exe" goto fail

echo.
echo ============================================
echo  BITTI!  Siteye yukleyecegin dosya:
echo  %~dp0output\KunefeLauncher_Setup.exe
echo ============================================
explorer "%~dp0output"
pause
exit /b 0

:findpython
set "PY="
if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" set "PY=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
if defined PY exit /b 0
python --version >nul 2>&1
if not errorlevel 1 set "PY=python"
exit /b 0

:nopython
echo.
echo Python otomatik kurulamadi. https://www.python.org/downloads/ adresinden
echo Python 3.12 kur ("Add python.exe to PATH" kutusunu isaretle), sonra bu dosyayi tekrar calistir.
pause
exit /b 1

:fail
echo.
echo Bir hata olustu. Yukaridaki mesaji kontrol et.
pause
exit /b 1
