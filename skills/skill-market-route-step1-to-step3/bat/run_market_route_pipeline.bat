@echo off
setlocal
set SCRIPT_DIR=%~dp0
set SKILL_DIR=%SCRIPT_DIR%..
set ROOT_DIR=%SKILL_DIR%\..
python "%SKILL_DIR%\scripts\run_market_route_pipeline.py" --root "%ROOT_DIR%" %*
endlocal
