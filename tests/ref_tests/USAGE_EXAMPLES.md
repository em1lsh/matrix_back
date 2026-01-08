# Примеры использования рефакторинг-тестов

## Базовые команды

### Запуск всех тестов
```bash
# Все рефакторинг-тесты
pytest backend/tests/ref_tests/ -v

# С кратким выводом
pytest backend/tests/ref_tests/ -v --tb=short

# С подробным выводом
pytest backend/tests/ref_tests/ -v --tb=long
```

### Запуск конкретных тестов
```bash
# Один файл
pytest backend/tests/ref_tests/test_ref_market.py -v

# Один класс
pytest backend/tests/ref_tests/test_ref_market.py::TestRefMarket -v

# Один тест
pytest backend/tests/ref_tests/test_ref_market.py::TestRefMarket::test_get_salings_200 -v
```

### Запуск с фильтрацией
```bash
# Только тесты с "market" в имени
pytest backend/tests/ref_tests/ -k "market" -v

# Только тесты с "200" в имени (успешные кейсы)
pytest backend/tests/ref_tests/ -k "200" -v

# Исключить тесты с "insufficient" в имени
pytest backend/tests/ref_tests/ -k "not insufficient" -v
```

## Отладка

### Остановка на первой ошибке
```bash
pytest backend/tests/ref_tests/ -x
```

### Вывод print statements
```bash
pytest backend/tests/ref_tests/ -s
```

### Запуск с pdb (отладчик)
```bash
pytest backend/tests/ref_tests/ --pdb
```

### Повторный запуск только упавших тестов
```bash
# Первый запуск
pytest backend/tests/ref_tests/ -v

# Повторный запуск только упавших
pytest backend/tests/ref_tests/ --lf -v
```

## Покрытие кода

### Запуск с покрытием
```bash
# Базовое покрытие
pytest backend/tests/ref_tests/ --cov=app/api/routers

# С HTML отчетом
pytest backend/tests/ref_tests/ --cov=app/api/routers --cov-report=html

# Открыть отчет
open htmlcov/index.html  # Mac
start htmlcov/index.html  # Windows
xdg-open htmlcov/index.html  # Linux
```

### Покрытие конкретного модуля
```bash
# Только market роутер
pytest backend/tests/ref_tests/test_ref_market.py --cov=app/api/routers/market

# Только nft роутер
pytest backend/tests/ref_tests/test_ref_nft.py --cov=app/api/routers/nft
```

## Производительность

### Измерение времени выполнения
```bash
# Показать 10 самых медленных тестов
pytest backend/tests/ref_tests/ --durations=10

# Показать все тесты с временем
pytest backend/tests/ref_tests/ --durations=0
```

### Параллельный запуск
```bash
# Установить pytest-xdist
pip install pytest-xdist

# Запуск в 4 процесса
pytest backend/tests/ref_tests/ -n 4

# Автоматическое определение количества процессов
pytest backend/tests/ref_tests/ -n auto
```

## Интеграция в workflow

### Pre-commit hook
Создайте файл `.git/hooks/pre-commit`:
```bash
#!/bin/bash
echo "Running refactoring tests..."
pytest backend/tests/ref_tests/ -v --tb=short
if [ $? -ne 0 ]; then
    echo "❌ Tests failed! Commit aborted."
    exit 1
fi
echo "✅ All tests passed!"
```

Сделайте его исполняемым:
```bash
chmod +x .git/hooks/pre-commit
```

### GitHub Actions
Создайте файл `.github/workflows/ref_tests.yml`:
```yaml
name: Refactoring Tests

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main, develop ]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        cd backend
        pip install poetry
        poetry install
    
    - name: Run refactoring tests
      run: |
        cd backend
        poetry run pytest tests/ref_tests/ -v --tb=short
```

### GitLab CI
Создайте файл `.gitlab-ci.yml`:
```yaml
ref_tests:
  stage: test
  image: python:3.11
  script:
    - cd backend
    - pip install poetry
    - poetry install
    - poetry run pytest tests/ref_tests/ -v --tb=short
  only:
    - main
    - develop
    - merge_requests
```

## Сценарии использования

### Сценарий 1: Рефакторинг эндпоинта
```bash
# 1. Запустить тесты ДО рефакторинга
pytest backend/tests/ref_tests/test_ref_market.py::TestRefMarket::test_get_salings_200 -v

# 2. Провести рефакторинг в app/api/routers/market.py

# 3. Запустить тесты ПОСЛЕ рефакторинга
pytest backend/tests/ref_tests/test_ref_market.py::TestRefMarket::test_get_salings_200 -v

# 4. Если тест упал - исправить код
```

### Сценарий 2: Добавление нового эндпоинта
```bash
# 1. Добавить эндпоинт в app/api/routers/market.py

# 2. Добавить тест в backend/tests/ref_tests/test_ref_market.py

# 3. Запустить новый тест
pytest backend/tests/ref_tests/test_ref_market.py::TestRefMarket::test_new_endpoint_200 -v

# 4. Обновить COVERAGE.md
```

### Сценарий 3: Проверка всех эндпоинтов после изменений
```bash
# Запустить все тесты
pytest backend/tests/ref_tests/ -v

# Если есть ошибки - посмотреть детали
pytest backend/tests/ref_tests/ -v --tb=long

# Исправить и запустить только упавшие
pytest backend/tests/ref_tests/ --lf -v
```

### Сценарий 4: Проверка производительности
```bash
# Запустить с измерением времени
pytest backend/tests/ref_tests/ --durations=10

# Если какой-то тест медленный - оптимизировать
pytest backend/tests/ref_tests/test_ref_market.py::TestRefMarket::test_slow_endpoint -v --durations=0
```

## Отчеты

### JUnit XML отчет
```bash
pytest backend/tests/ref_tests/ --junitxml=report.xml
```

### HTML отчет
```bash
# Установить pytest-html
pip install pytest-html

# Создать отчет
pytest backend/tests/ref_tests/ --html=report.html --self-contained-html
```

### JSON отчет
```bash
# Установить pytest-json-report
pip install pytest-json-report

# Создать отчет
pytest backend/tests/ref_tests/ --json-report --json-report-file=report.json
```

## Мониторинг

### Запуск в watch режиме
```bash
# Установить pytest-watch
pip install pytest-watch

# Запустить в watch режиме
ptw backend/tests/ref_tests/ -- -v
```

### Уведомления
```bash
# Установить pytest-notifier
pip install pytest-notifier

# Запустить с уведомлениями
pytest backend/tests/ref_tests/ --notifier
```

## Troubleshooting

### Проблема: Тесты падают из-за конфликта данных
```bash
# Решение: Очистить тестовую БД
cd backend
python tests/clean_test_data.py

# Запустить тесты снова
pytest backend/tests/ref_tests/ -v
```

### Проблема: Тесты медленно выполняются
```bash
# Решение 1: Запустить параллельно
pytest backend/tests/ref_tests/ -n auto

# Решение 2: Найти медленные тесты
pytest backend/tests/ref_tests/ --durations=10

# Решение 3: Оптимизировать медленные тесты
```

### Проблема: Тест падает только в CI
```bash
# Решение: Запустить локально с теми же условиями
docker run -it python:3.11 bash
cd /app
pip install poetry
poetry install
poetry run pytest tests/ref_tests/ -v
```

## Полезные комбинации

### Быстрая проверка после изменений
```bash
pytest backend/tests/ref_tests/ -x --tb=short
```

### Детальная отладка конкретного теста
```bash
pytest backend/tests/ref_tests/test_ref_market.py::TestRefMarket::test_get_salings_200 -vv -s --tb=long
```

### Проверка покрытия с отчетом
```bash
pytest backend/tests/ref_tests/ --cov=app/api/routers --cov-report=html --cov-report=term
```

### Запуск с профилированием
```bash
# Установить pytest-profiling
pip install pytest-profiling

# Запустить с профилированием
pytest backend/tests/ref_tests/ --profile
```

## Интеграция с IDE

### PyCharm
1. Открыть `backend/tests/ref_tests/test_ref_market.py`
2. Кликнуть на зеленую стрелку рядом с тестом
3. Выбрать "Run" или "Debug"

### VS Code
1. Установить расширение "Python Test Explorer"
2. Открыть панель тестов (Ctrl+Shift+P → "Test: Focus on Test Explorer View")
3. Запустить тесты из панели

### Vim/Neovim
```vim
" Запустить текущий тест
:!pytest %::TestRefMarket::test_get_salings_200 -v

" Запустить все тесты в файле
:!pytest % -v
```

## Автоматизация

### Makefile
Создайте `backend/Makefile`:
```makefile
.PHONY: ref-tests
ref-tests:
	pytest tests/ref_tests/ -v --tb=short

.PHONY: ref-tests-fast
ref-tests-fast:
	pytest tests/ref_tests/ -x --tb=short

.PHONY: ref-tests-coverage
ref-tests-coverage:
	pytest tests/ref_tests/ --cov=app/api/routers --cov-report=html
```

Использование:
```bash
cd backend
make ref-tests
make ref-tests-fast
make ref-tests-coverage
```

### Shell скрипт
Создайте `backend/scripts/run_ref_tests.sh`:
```bash
#!/bin/bash
set -e

echo "🧪 Running refactoring tests..."

cd "$(dirname "$0")/.."
source .venv/bin/activate

pytest tests/ref_tests/ -v --tb=short

if [ $? -eq 0 ]; then
    echo "✅ All tests passed!"
else
    echo "❌ Some tests failed!"
    exit 1
fi
```

## Заключение

Рефакторинг-тесты - это инструмент для быстрой проверки работоспособности API. Используйте их:
- ✅ Перед и после рефакторинга
- ✅ В CI/CD pipeline
- ✅ Для быстрой проверки изменений
- ✅ Для мониторинга состояния API

Не используйте их:
- ❌ Для детального тестирования бизнес-логики
- ❌ Для тестирования производительности
- ❌ Для тестирования edge cases
