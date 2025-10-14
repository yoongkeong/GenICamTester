@echo off
REM Run all camera simulation tests with pytest
SETLOCAL
cd /d %~dp0
python -m pytest -q --simulate
ENDLOCAL
