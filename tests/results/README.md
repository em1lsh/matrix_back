# Результаты тестов тяжелых эндпоинтов

Эта директория содержит результаты тестов ДО и ПОСЛЕ рефакторинга.

## Файлы

### baseline_heavy_endpoints.txt
Результаты тестов **ДО** рефакторинга.

**Создать:**
```bash
cd backend
poetry run pytest tests/test_heavy_endpoints.py -v > tests/results/baseline_heavy_endpoints.txt
```

### optimized_heavy_endpoints.txt
Результаты тестов **ПОСЛЕ** рефакторинга.

**Создать:**
```bash
cd backend
poetry run pytest tests/test_heavy_endpoints.py -v > tests/results/optimized_heavy_endpoints.txt
```

## Сравнение

```bash
diff tests/results/baseline_heavy_endpoints.txt tests/results/optimized_heavy_endpoints.txt
```

**Все тесты должны проходить ДО и ПОСЛЕ!**
