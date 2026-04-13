@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
set "DEFAULT_INPUT_DIR=%SCRIPT_DIR%.."
set "DEFAULT_OUTPUT_DIR=%SCRIPT_DIR%outputs"

python "%SCRIPT_DIR%run_market_m01_to_m02.py" --input-dir "%DEFAULT_INPUT_DIR%" --output-dir "%DEFAULT_OUTPUT_DIR%" %*
exit /b %ERRORLEVEL%
