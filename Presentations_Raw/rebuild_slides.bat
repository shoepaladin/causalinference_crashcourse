@echo off
setlocal
title Rebuild causal inference slide decks
cd /d "%~dp0"

REM The build scripts print arrow/check glyphs; the Windows console defaults to
REM cp1252, so force UTF-8 for this run.
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8

echo.
echo ====================================================================
echo   Rebuilding the causal inference slide decks
echo   Folder: %CD%
echo ====================================================================
echo.

where python >nul 2>&1
if errorlevel 1 goto :nopython
where node >nul 2>&1
if errorlevel 1 goto :nonode

echo [1/4] Python packages
python -c "import nbconvert" >nul 2>&1
if errorlevel 1 (
    echo       nbconvert missing - installing...
    python -m pip install --quiet "nbconvert>=7.0"
    if errorlevel 1 goto :fail
) else (
    echo       nbconvert OK
)

echo [2/4] Vendored reveal.js / MathJax / playwright
if not exist "node_modules" (
    echo       node_modules missing - running npm install...
    call npm install
    if errorlevel 1 goto :fail
) else (
    echo       node_modules OK
)

REM Ask playwright where its Chromium is and whether that file exists, rather
REM than guessing from a folder name - the browser revision changes when the
REM playwright package is upgraded, and a stale folder would pass a name check.
echo [3/4] Headless Chromium
node -e "const{chromium}=require('playwright');process.exit(require('fs').existsSync(chromium.executablePath())?0:1)" >nul 2>&1
if errorlevel 1 (
    echo       Chromium missing or outdated - downloading...
    call npx playwright install chromium
    if errorlevel 1 goto :fail
) else (
    echo       Chromium OK
)

echo.
echo [4/4] Building PDFs into Updated_v2 ...
echo.
python build_pdfs.py %*
if errorlevel 1 goto :fail

echo.
echo Done. Updated PDFs are in: %CD%\Updated_v2
echo Commit the .pdf files; the .slides.html files are local build artifacts.
goto :end

:nopython
echo ERROR: "python" was not found on your PATH.
echo Install Python 3.9+ from python.org, ticking "Add python.exe to PATH".
goto :end

:nonode
echo ERROR: "node" was not found on your PATH.
echo Install Node.js LTS from nodejs.org, then re-run this script.
goto :end

:fail
echo.
echo BUILD FAILED - read the messages above.

:end
echo.
pause
