@echo off
setlocal enabledelayedexpansion

echo ========================================
echo Creating Test User in Docker DB
echo ========================================
echo.

REM Генерируем timestamp (текущее время + 30 минут = 1800 секунд)
for /f %%i in ('powershell -command "[int]([DateTimeOffset]::Now.ToUnixTimeSeconds() + 1800)"') do set TIMESTAMP=%%i

REM Генерируем UUID
for /f %%i in ('powershell -command "[guid]::NewGuid().ToString()"') do set UUID=%%i

REM Формируем токен
set TOKEN=%TIMESTAMP%_%UUID%

REM Генерируем memo (16 случайных hex символов)
for /f %%i in ('powershell -command "-join ((48..57) + (97..102) | Get-Random -Count 16 | ForEach-Object {[char]$_})"') do set MEMO=%%i

set USER_ID=999999999
set BALANCE=1000000000000

echo Token: %TOKEN%
echo Memo: %MEMO%
echo.

REM Создаем пользователя через SQL (в БД loadtest_db)
docker exec backend-db-1 psql -U postgres -d loadtest_db -c "INSERT INTO users (id, token, memo, language, market_balance, payment_status, subscription_status, \"group\") VALUES (%USER_ID%, '%TOKEN%', '%MEMO%', 'en', %BALANCE%, true, true, 'member') ON CONFLICT (id) DO UPDATE SET token = '%TOKEN%', market_balance = %BALANCE%, payment_status = true, subscription_status = true;"

REM Сохраняем токен в файл (без пробела в конце)
echo|set /p="%TOKEN%" > test_token.txt

echo.
echo ========================================
echo User created/updated!
echo Token saved to test_token.txt
echo ========================================
pause
