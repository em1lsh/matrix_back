#!/bin/bash

# Генерируем токен
TIMESTAMP=$(($(date +%s) + 1800))  # +30 минут
UUID=$(cat /proc/sys/kernel/random/uuid)
TOKEN="${TIMESTAMP}_${UUID}"

# Генерируем memo
MEMO=$(openssl rand -hex 8)

USER_ID=999999999
BALANCE=1000000000000

echo "Creating user in database..."
echo "Token: $TOKEN"
echo "Memo: $MEMO"

# Создаем пользователя через SQL
docker exec backend-db-1 psql -U postgres -d postgres <<EOF
INSERT INTO users (id, token, memo, language, market_balance, payment_status, subscription_status, "group")
VALUES ($USER_ID, '$TOKEN', '$MEMO', 'en', $BALANCE, true, true, 'member')
ON CONFLICT (id) DO UPDATE
SET token = '$TOKEN',
    market_balance = $BALANCE,
    payment_status = true,
    subscription_status = true;
EOF

# Сохраняем токен в файл
echo "$TOKEN" > tests/load/test_token.txt

echo "✅ User created/updated!"
echo "Token saved to tests/load/test_token.txt"
