@echo off
chcp 65001 >nul

echo ==========================================================================
echo  UNIVERSAL SCRAPER v7.0 - АВТОМАТИЧЕСКАЯ УСТАНОВКА
   email: malkodiro@gmail.com
   пароль: встроен в программу
   браузер: Firefox Portable
   диск: D: (рекомендуется)
echo ==========================================================================
echo.

:: ЭТАП 1: Проверка Python
echo [1/4] Проверка Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo   Установка Python 3.11...
    powershell -Command "Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.11.6/python-3.11.6-amd64.exe' -OutFile '%~dp0python_installer.exe' -UseBasicParsing"
    start /wait "" "%~dp0python_installer.exe" /quiet InstallAllUsers=1 PrependPath=1 Include_test=0
    del "%~dp0python_installer.exe" >nul 2>&1
    python --version >nul 2>&1
    if %errorlevel% neq 0 (
        echo ERROR: Python не установлен
        pause
        exit /b
    )
    echo   Python установлен!
) else (
    echo   Python уже есть
)

:: ЭТАП 2: Зависимости
echo.
echo [2/4] Установка зависимостей...
pip install selenium beautifulsoup4 python-docx markdownify webdriver-manager --quiet --upgrade 2>nul
if %errorlevel% neq 0 (
    pip install selenium beautifulsoup4 python-docx markdownify webdriver-manager
)
echo   Зависимости готовы!

:: ЭТАП 3: Firefox Portable
echo.
echo [3/4] Установка Firefox Portable...
if not exist "%~dp0BROWSER" mkdir "%~dp0BROWSER"
if not exist "%~dp0BROWSER\FirefoxPortable\FirefoxPortable.exe" (
    powershell -Command "Invoke-WebRequest -Uri 'https://download.portableapps.com/portableapps/firefoxportable/FirefoxPortable_128.0_English.paf.exe' -OutFile '%~dp0BROWSER\installer.exe' -UseBasicParsing"
    start /wait "" "%~dp0BROWSER\installer.exe" /SILENT /DIR="%~dp0BROWSER\FirefoxPortable"
    timeout /t 5 >nul
    del "%~dp0BROWSER\installer.exe" >nul 2>&1
    echo   Firefox установлен!
) else (
    echo   Firefox уже есть
)

:: ЭТАП 4: Профиль
echo.
echo [4/4] Настройка профиля...
if not exist "%~dp0BROWSER\firefox_profile" mkdir "%~dp0BROWSER\firefox_profile"

:: ЗАПУСК
echo.
echo ==========================================================================
echo   ВСЁ ГОТОВО! Запускаем программу...
echo ==========================================================================
echo.
python "%~dp0UNIVERSAL_SMART_SCRAPER.py"
pause
