#!/bin/bash
# Запуск рефакторинг-тестов (ref_tests)
# Эти тесты проверяют что все эндпоинты возвращают статус 200

echo "========================================"
echo "Running Refactoring Tests (ref_tests)"
echo "========================================"
echo ""

cd "$(dirname "$0")/.."

# Активируем виртуальное окружение
source .venv/bin/activate

# Запускаем тесты
pytest tests/ref_tests/ -v --tb=short

echo ""
echo "========================================"
echo "Tests completed!"
echo "========================================"
