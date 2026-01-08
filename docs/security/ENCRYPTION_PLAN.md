# План шифрования чувствительных данных

## Дата: 2024-12-02
## Приоритет: КРИТИЧЕСКИЙ (БЛОКЕР РЕЛИЗА)

---

## Проблемы

### ПРОБЛЕМА 1: Пароли в открытом виде
**Файл:** `backend/project/app/db/models/user.py:73`
**Модель:** `Account.password`

**Текущее состояние:**
```python
password = Column(String(255), nullable=True, default=None)
```

**Риск:** КРИТИЧЕСКИЙ
- Полный компромисс при утечке БД
- Доступ к Telegram аккаунтам пользователей
- Нарушение GDPR и других регуляций

---

### ПРОБЛЕМА 2: Auth_data в открытом виде
**Файл:** `backend/project/app/db/models/tonnel.py:22`
**Модель:** `TonnelAccount.auth_data`

**Текущее состояние:**
```python
auth_data = Column(Text, nullable=False)  # authData для авторизации
```

**Риск:** КРИТИЧЕСКИЙ
- Доступ к аккаунтам Tonnel Market
- Возможность совершать операции от имени пользователя
- Кража NFT и средств

---

## Решение

### Подход 1: Хеширование паролей (Account.password)

**Библиотека:** `passlib` с `bcrypt`

**Почему bcrypt:**
- Индустриальный стандарт для хеширования паролей
- Встроенная защита от brute-force (cost factor)
- Автоматическое добавление соли
- Невозможность восстановить исходный пароль

**Установка:**
```bash
poetry add passlib[bcrypt]
```

**Реализация:**
```python
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Хеширование
password_hash = pwd_context.hash(plain_password)

# Проверка
is_valid = pwd_context.verify(plain_password, password_hash)
```

---

### Подход 2: Шифрование auth_data (TonnelAccount.auth_data)

**Библиотека:** `cryptography` с `Fernet` (AES-256)

**Почему Fernet:**
- Симметричное шифрование (можно расшифровать)
- AES-256 в режиме CBC
- Встроенная аутентификация (HMAC)
- Простой API

**Установка:**
```bash
poetry add cryptography
```

**Реализация:**
```python
from cryptography.fernet import Fernet
import base64
import os

# Генерация ключа (один раз, хранить в .env)
encryption_key = Fernet.generate_key()

# Инициализация
cipher = Fernet(encryption_key)

# Шифрование
encrypted_data = cipher.encrypt(plain_data.encode())

# Расшифровка
decrypted_data = cipher.decrypt(encrypted_data).decode()
```

---

## План миграции

### Этап 1: Подготовка

1. **Установить зависимости:**
   ```bash
   cd backend
   poetry add passlib[bcrypt] cryptography
   ```

2. **Создать утилиты шифрования:**
   - `backend/project/app/utils/security.py`
   - Функции для хеширования паролей
   - Функции для шифрования/расшифровки данных
   - Управление ключами шифрования

3. **Добавить переменные окружения:**
   ```env
   # .env
   ENCRYPTION_KEY=<base64_encoded_key>
   ```

---

### Этап 2: Миграция БД

#### 2.1 Добавить новые колонки

**Для Account:**
```python
# Alembic migration
password_hash = Column(String(255), nullable=True, default=None)
```

**Для TonnelAccount:**
```python
# Alembic migration
auth_data_encrypted = Column(Text, nullable=True, default=None)
```

#### 2.2 Мигрировать существующие данные

**Скрипт миграции:**
```python
# Для паролей
for account in accounts:
    if account.password:
        account.password_hash = pwd_context.hash(account.password)

# Для auth_data
for tonnel_account in tonnel_accounts:
    if tonnel_account.auth_data:
        tonnel_account.auth_data_encrypted = cipher.encrypt(
            tonnel_account.auth_data.encode()
        ).decode()
```

#### 2.3 Удалить старые колонки

```python
# Alembic migration
op.drop_column('accounts', 'password')
op.drop_column('tonnel_accounts', 'auth_data')
```

---

### Этап 3: Обновление кода

#### 3.1 Обновить модели

**Account:**
```python
class Account(Base):
    # ...
    password_hash = Column(String(255), nullable=True, default=None)
    
    def set_password(self, password: str):
        """Установить пароль (хеширует автоматически)"""
        from app.utils.security import hash_password
        self.password_hash = hash_password(password)
    
    def verify_password(self, password: str) -> bool:
        """Проверить пароль"""
        from app.utils.security import verify_password
        return verify_password(password, self.password_hash)
```

**TonnelAccount:**
```python
class TonnelAccount(Base):
    # ...
    auth_data_encrypted = Column(Text, nullable=False)
    
    def set_auth_data(self, auth_data: str):
        """Установить auth_data (шифрует автоматически)"""
        from app.utils.security import encrypt_data
        self.auth_data_encrypted = encrypt_data(auth_data)
    
    def get_auth_data(self) -> str:
        """Получить auth_data (расшифровывает автоматически)"""
        from app.utils.security import decrypt_data
        return decrypt_data(self.auth_data_encrypted)
```

#### 3.2 Обновить использование

**Найти все места где используется:**
- `account.password` → `account.set_password()` / `account.verify_password()`
- `tonnel_account.auth_data` → `tonnel_account.set_auth_data()` / `tonnel_account.get_auth_data()`

---

### Этап 4: Тестирование

1. **Unit-тесты:**
   - Тест хеширования паролей
   - Тест шифрования/расшифровки
   - Тест методов моделей

2. **Интеграционные тесты:**
   - Тест создания аккаунта с паролем
   - Тест авторизации с паролем
   - Тест работы с Tonnel API

3. **Миграционные тесты:**
   - Тест миграции существующих данных
   - Тест обратной совместимости

---

## Безопасность ключей

### Генерация ключа шифрования

```python
from cryptography.fernet import Fernet

# Генерировать один раз
key = Fernet.generate_key()
print(key.decode())  # Сохранить в .env
```

### Хранение ключей

**НЕ КОММИТИТЬ В GIT!**

1. **Development:** `.env` (в .gitignore)
2. **Production:** Переменные окружения или секреты (AWS Secrets Manager, Vault)
3. **Backup:** Безопасное хранилище (зашифрованное, офлайн)

### Ротация ключей

При компрометации ключа:
1. Сгенерировать новый ключ
2. Расшифровать все данные старым ключом
3. Зашифровать новым ключом
4. Обновить переменную окружения

---

## Риски и митигация

### Риск 1: Потеря ключа шифрования
**Последствия:** Невозможность расшифровать auth_data
**Митигация:** 
- Резервное копирование ключа
- Документирование процесса восстановления
- Возможность пересоздания auth_data через повторную авторизацию

### Риск 2: Ошибка в миграции
**Последствия:** Потеря данных
**Митигация:**
- Полный бэкап БД перед миграцией
- Тестирование на копии БД
- Возможность отката

### Риск 3: Проблемы с производительностью
**Последствия:** Медленная авторизация
**Митигация:**
- bcrypt с оптимальным cost factor (12-13)
- Кеширование расшифрованных данных (с осторожностью)
- Мониторинг производительности

---

## Критерии приемки

- ✅ Пароли хешируются с bcrypt
- ✅ Auth_data шифруется с Fernet (AES-256)
- ✅ Старые колонки удалены
- ✅ Все существующие данные мигрированы
- ✅ Код обновлен для использования новых методов
- ✅ Тесты написаны и проходят
- ✅ Ключи шифрования в безопасности
- ✅ Документация обновлена

---

## Оценка времени

- **Этап 1 (Подготовка):** 2 часа
- **Этап 2 (Миграция БД):** 3 часа
- **Этап 3 (Обновление кода):** 4 часа
- **Этап 4 (Тестирование):** 3 часа

**Итого:** ~12 часов (1.5 рабочих дня)

---

## Следующие шаги

1. Создать утилиты шифрования
2. Создать Alembic миграцию
3. Написать скрипт миграции данных
4. Обновить модели
5. Обновить код использования
6. Написать тесты
7. Протестировать на dev окружении
8. Задеплоить на production
