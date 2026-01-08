@echo off
echo ========================================
echo Load Test: 1000 Users
echo ========================================
echo.
echo This will simulate 1000 concurrent users
echo.
echo Make sure the server is running:
echo   - Docker: run docker-start-loadtest.bat
echo   - Local: run start_load_test_server.bat
echo.
pause

cd /d "%~dp0"

echo Starting load test...
echo.
poetry run locust -f locustfile_uow.py ^
    --headless ^
    --users 1000 ^
    --spawn-rate 50 ^
    --run-time 60s ^
    --host http://localhost:8000 ^
    --html report_1000_users.html ^
    --csv report_1000_users

echo.
echo ========================================
echo Test completed!
echo Check report_1000_users.html for results
echo ========================================
pause
