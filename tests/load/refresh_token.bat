@echo off
echo ========================================
echo Refreshing Load Test Token
echo ========================================
echo.

cd /d "%~dp0"
cd ..\..

echo Generating new token...
poetry run python tests/load/refresh_token.py

echo.
pause
