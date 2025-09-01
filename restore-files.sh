#!/usr/bin/env bash
set -euo pipefail

# Простой скрипт для восстановления файлов проекта

PROJECT_DIR="/data/crystall-budget"
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}Восстановление файлов проекта...${NC}"

# Проверяем где находимся
current_dir="$(pwd)"
echo "Текущая директория: ${current_dir}"

# Если мы в /data/crystall-budget и файлов нет
if [[ "${current_dir}" == "${PROJECT_DIR}" ]] && [[ ! -d "api" ]]; then
    echo -e "${RED}Файлы удалены. Нужно загрузить проект заново.${NC}"
    echo
    echo "Варианты:"
    echo "1. Скачать с Git:"
    echo "   cd /tmp"
    echo "   git clone <your-repo> crystall-budget"
    echo "   cd crystall-budget"
    echo "   sudo ./deploy.sh"
    echo
    echo "2. Загрузить файлы по SCP:"
    echo "   scp -r crystall-budget/* root@server:/data/crystall-budget/"
    echo "   cd /data/crystall-budget"
    echo "   sudo ./deploy.sh"
    exit 1
fi

# Если у нас есть исходные файлы
if [[ -d "api" && -d "web" ]]; then
    echo -e "${GREEN}✓ Файлы проекта найдены${NC}"
    
    # Копируем в нужное место если нужно
    if [[ "${current_dir}" != "${PROJECT_DIR}" ]]; then
        echo "Копирование в ${PROJECT_DIR}..."
        mkdir -p "${PROJECT_DIR}"
        cp -r api web *.sh *.service Caddyfile README.md CLAUDE.md "${PROJECT_DIR}/"
        chown -R crystall:crystall "${PROJECT_DIR}"
        echo -e "${GREEN}✓ Файлы скопированы${NC}"
        
        echo "Теперь выполните:"
        echo "  cd ${PROJECT_DIR}"
        echo "  sudo ./deploy.sh"
    else
        echo -e "${GREEN}✓ Уже в правильной директории${NC}"
        echo "Можно запускать: sudo ./deploy.sh"
    fi
else
    echo -e "${RED}Файлы api/ и web/ не найдены${NC}"
    echo "Убедитесь что вы в директории с проектом"
fi