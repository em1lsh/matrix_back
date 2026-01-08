@echo off
REM Запуск рефакторинг-тестов (ref_tests)
REM Эти тесты проверяют что все эндпоинты возвращают статус 200

echo ========================================
echo Running Refactoring Tests (ref_tests)
echo ========================================
echo.

cd /d "%~dp0"
cd ..

REM Активируем виртуальное окружение
call .venv\Scripts\activate.bat

REM Запускаем тесты
pytest tests/ref_tests/ -v --tb=short

echo.
echo ========================================
echo Tests completed!
echo ========================================
pause
