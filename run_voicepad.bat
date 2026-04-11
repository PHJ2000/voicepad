@echo off
setlocal
set "APP_DIR=%~dp0"
set "HOTKEY_RUNNER=%APP_DIR%run_codex_hotkeys.bat"
set "APP_RUNNER=%APP_DIR%run_codex_dictation.bat"

if not exist "%APP_RUNNER%" (
  echo Voicepad app launcher not found: "%APP_RUNNER%"
  exit /b 1
)

if exist "%HOTKEY_RUNNER%" (
  call "%HOTKEY_RUNNER%"
  if errorlevel 1 (
    echo Voicepad hotkey launcher failed. Continuing with app only.
  ) else (
    timeout /t 1 /nobreak >nul
  )
)

call "%APP_RUNNER%" %*
exit /b %ERRORLEVEL%
