@echo off
setlocal
set "APP_DIR=%~dp0"
set "DIST_EXE=%APP_DIR%dist\Voicepad.exe"
set "PYTHONW=%APP_DIR%.venv\Scripts\pythonw.exe"
set "PYTHON=%APP_DIR%.venv\Scripts\python.exe"

if exist "%DIST_EXE%" (
  start "" "%DIST_EXE%" %*
  exit /b 0
)

if exist "%PYTHONW%" (
  start "" "%PYTHONW%" "%APP_DIR%codex_dictation.py" %*
  exit /b 0
)

if exist "%PYTHON%" (
  start "" "%PYTHON%" "%APP_DIR%codex_dictation.py" %*
  exit /b 0
)

echo Could not find Python in "%APP_DIR%.venv\Scripts".
exit /b 1
