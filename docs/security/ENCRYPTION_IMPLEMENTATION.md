# Инструкция по внедрению шифрования

## Дата: 2024-12-02
## Статус: Готово к применению

---

## Что сделано

### ✅ 1. Утилиты шифрования
**Файл:** `backend/project/app/utils/security.py`

Функции:
- `hash_password(password)` - хеширование паролей с bcrypt
- `verify_password(plain, hashed)` - проверка пароля
- `encrypt_data(data)` - шифрование данных с Fernet (AES-256)
- `decrypt_data(encrypted)` - расшифровка данных
- `generate_encryption_key()` - генерация ключа

### ✅ 2. Конфигурация
**Файл:** `backend/project/app/configs/__init__.py`

Добавлено поле:
```python
encryption_key: str = Field(default="")
```

### ✅ 3. Зависимости
**Файл:** `backend/pyproject.toml`

Добавлено:
```toml
passlib = {extras = ["bcrypt"], version = "^1.7.4"}
bcrypt = "^4.1.2"
```

`cryptography` уже был установлен.

### ✅ 4. Миграция БД
**Файл:** `backend/project/alembic/versions/add_encryption_columns.py`

Добавляет колонки:
- `accounts.password_hash`
- `tonnel_accounts.auth_data_encrypted`

### ✅ 5. Скрипт миграции данных
**Файл:** `backend/project/migrate_sensitive_data.py`

Мигрирует существующие данные в зашифрованный формат.

### ✅ 6. Генератор ключа
**Файл:** `backend/project/generate_encryption_key.py`

Генерирует ключ шифрования для .env

---

## Порядок применения

### Шаг 1: Установить зависимости

```bash
cd backend
poetry install
```

### Шаг 2: Сгенерировать ключ шифрования

```bash
cd project
python generate_encryption_key.py
```

Скопируйте сгенерированный ключ.

### Шаг 3: Добавить ключ в .env

```bash
# backend/.env
ENCRYPTION_KEY=<generated_key_here>
```

**⚠️ ВАЖНО:** Не коммитьте ключ в git!

### Шаг 4: Сделать бэкап БД

```bash
# Для PostgreSQL
docker compose exec db pg_dump -U loadtest_user loadtest_db > backup_before_encryption.sql

# Или через docker
docker compose exec db pg_dump -U loadtest_user loadtest_db | gzip > backup_$(date +%Y%m%d_%H%M%S).sql.gz
```

### Шаг 5: Применить миграцию БД

```bash
cd project
poetry run alembic upgrade head
```

Это добавит новые колонки `password_hash` и `auth_data_encrypted`.

### Шаг 6: Мигрировать существующие данные

```bash
cd project
python migrate_sensitive_data.py
```

Скрипт:
1. Захеширует все пароли
2. Зашифрует все auth_data
3. Проверит результаты

### Шаг 7: Обновить модели (TODO)

Нужно обновить модели чтобы использовать новые колонки:

**Account:**
```python
class Account(Base):
    # Старое (удалить после миграции)
    # password = Column(String(255), nullable=True, default=None)
    
    # Новое
    password_hash = Column(String(255), nullable=True, default=None)
    
    def set_password(self, password: str):
        from app.utils.security import hash_password
        self.password_hash = hash_password(password)
    
    def verify_password(self, password: str) -> bool:
        from app.utils.security import verify_password
        return verify_password(password, self.password_hash)
```

**TonnelAccount:**
```python
class TonnelAccount(Base):
    # Старое (удалить после миграции)
    # auth_data = Column(Text, nullable=False)
    
    # Новое
    auth_data_encrypted = Column(Text, nullable=False)
    
    def set_auth_data(self, auth_data: str):
        from app.utils.security import encrypt_data
        self.auth_data_encrypted = encrypt_data(auth_data)
    
    def get_auth_data(self) -> str:
        from app.utils.security import decrypt_data
        return decrypt_data(self.auth_data_encrypted)
```

### Шаг 8: Обновить код использования (TODO)

Найти все места где используется:
- `account.password` → заменить на `account.set_password()` / `account.verify_password()`
- `tonnel_account.auth_data` → заменить на `tonnel_account.set_auth_data()` / `tonnel_account.get_auth_data()`

### Шаг 9: Тестирование

1. Проверить что приложение запускается
2. Проверить авторизацию с паролем
3. Проверить работу с Tonnel API
4. Проверить что новые пароли хешируются
5. Проверить что новые auth_data шифруются

### Шаг 10: Удалить старые колонки

После успешного тестирования создать миграцию:

```bash
poetry run alembic revision -m "drop old password columns"
```

В миграции:
```python
def upgrade():
    op.drop_column('accounts', 'password')
    op.drop_column('tonnel_accounts', 'auth_data')

def downgrade():
    op.add_column('accounts', sa.Column('password', sa.String(255)))
    op.add_column('tonnel_accounts', sa.Column('auth_data', sa.Text()))
```

Применить:
```bash
poetry run alembic upgrade head
```

---

## Откат (если что-то пошло не так)

### Если миграция данных не завершилась:

1. Восстановить БД из бэкапа:
```bash
docker compose exec -T db psql -U loadtest_user loadtest_db < backup_before_encryption.sql
```

2. Откатить миграцию БД:
```bash
poetry run alembic downgrade -1
```

### Если нужно изменить ключ ��ифрования:

1. Сгенерировать новый ключ
2. Расшифровать данные старым ключом
3. Зашифровать новым ключом
4. Обновить .env

---

## Проверка безопасности

### Проверить что пароли захешированы:

```sql
SELECT id, password, password_hash FROM accounts LIMIT 5;
```

Должно быть:
- `password` - старый пароль (будет удален)
- `password_hash` - начинается с `$2b$` (bcrypt hash)

### Проверить что auth_data зашифрованы:

```sql
SELECT id, auth_data, auth_data_encrypted FROM tonnel_accounts LIMIT 5;
```

Должно быть:
- `auth_data` - старые данные (будут удалены)
- `auth_data_encrypted` - зашифрованная строка (base64)

---

## Мониторинг

После деплоя следить за:
- Временем авторизации (bcrypt может быть медленнее)
- Ошибками расшифровки (проблемы с ключом)
- Логами безопасности

---

## Следующие шаги

1. ⏳ Обновить модели Account и TonnelAccount
2. ⏳ Найти и обновить код использования
3. ⏳ Написать unit-тесты
4. ⏳ Протестировать на dev окружении
5. ⏳ Создать миграцию для удаления старых колонок
6. ⏳ Задеплоить на production

---

## Контакты

При проблемах:
- Проверить логи: `docker compose logs app`
- Проверить ключ: `echo $ENCRYPTION_KEY`
- Проверить БД: `docker compose exec db psql -U loadtest_user loadtest_db`
