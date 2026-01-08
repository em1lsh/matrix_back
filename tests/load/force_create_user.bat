@echo off
echo ========================================
echo Init DB and Create Test User
echo ========================================
echo.

cd /d "%~dp0\..\..\"

REM Запускаем через poetry
poetry run python tests/load/init_db_and_create_user.py

echo.
echo ========================================
pause
