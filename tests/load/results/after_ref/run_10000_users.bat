@echo off
echo ========================================
echo Load Test: 10,000 Users
echo ========================================
echo.
echo This will simulate 10,000 concurrent users
echo.
echo Make sure the server is running in Docker
echo.
pause

cd /d "%~dp0"

echo Starting load test...
echo.
poetry run locust -f locustfile_uow.py ^
    --headless ^
    --users 10000 ^
    --spawn-rate 100 ^
    --run-time 120s ^
    --host http://127.0.0.1:8000 ^
    --html report_10000_users.html ^
    --csv report_10000_users

echo.
echo ========================================
echo Test completed!
echo Check report_10000_users.html for results
echo ========================================
pause
