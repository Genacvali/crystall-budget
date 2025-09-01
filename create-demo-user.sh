#!/usr/bin/env bash
set -euo pipefail

GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}Создание демо-пользователя...${NC}"

# Создаем демо-пользователя в базе
psql "postgres://crystall:adminDII@127.0.0.1:5432/crystall" -c "
INSERT INTO \"User\"(id, email, \"passwordHash\") 
VALUES (gen_random_uuid(), 'demo@crystall.local', 'demo1234') 
ON CONFLICT (email) DO UPDATE SET \"passwordHash\" = 'demo1234';
"

echo -e "${GREEN}✓ Демо-пользователь создан: demo@crystall.local / demo1234${NC}"

# Создаем еще несколько тестовых пользователей
psql "postgres://crystall:adminDII@127.0.0.1:5432/crystall" -c "
INSERT INTO \"User\"(id, email, \"passwordHash\") 
VALUES (gen_random_uuid(), 'test@test.com', '123456') 
ON CONFLICT (email) DO UPDATE SET \"passwordHash\" = '123456';

INSERT INTO \"User\"(id, email, \"passwordHash\") 
VALUES (gen_random_uuid(), 'admin@crystall.local', 'admin123') 
ON CONFLICT (email) DO UPDATE SET \"passwordHash\" = 'admin123';
"

echo -e "${GREEN}✓ Тестовые пользователи созданы:${NC}"
echo "  test@test.com / 123456"
echo "  admin@crystall.local / admin123"

# Показываем всех пользователей
echo -e "\n${BLUE}Все пользователи в базе:${NC}"
psql "postgres://crystall:adminDII@127.0.0.1:5432/crystall" -c "
SELECT email, \"passwordHash\", \"createdAt\" FROM \"User\" ORDER BY \"createdAt\";
"

echo
echo -e "${GREEN}=========================================="
echo "        Демо-пользователи готовы!"
echo "==========================================${NC}"
echo
echo "🔑 Теперь можно войти с любым из аккаунтов:"
echo "  demo@crystall.local / demo1234"
echo "  test@test.com / 123456" 
echo "  admin@crystall.local / admin123"