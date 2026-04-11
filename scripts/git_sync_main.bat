@echo off
setlocal
set "SCRIPT_DIR=%~dp0"
echo [DEPRECATED] Use powershell -ExecutionPolicy Bypass -File ".\scripts\git_sync_repo_main.ps1" -StageAll
powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%git_sync_repo_main.ps1" %*
exit /b %errorlevel%
