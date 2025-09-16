#!/bin/bash
# Скрипт для исправления ошибки на продакшене

set -e

echo "🔧 Исправление ошибки python-dotenv на продакшене..."

# Активируем виртуальное окружение и устанавливаем python-dotenv
echo "📦 Установка python-dotenv в виртуальное окружение..."
source /opt/crystalbudget/venv/bin/activate
pip install python-dotenv>=1.0,<2.0

# Копируем обновленный app.py
echo "📄 Копирование обновленного app.py..."
cp /opt/crystall-budget/app.py /opt/crystalbudget/crystall-budget/app.py

# Копируем обновленный requirements.txt
echo "📄 Копирование обновленного requirements.txt..."
cp /opt/crystall-budget/requirements.txt /opt/crystalbudget/crystall-budget/requirements.txt

# Создаем .env файл если его нет
if [ ! -f /opt/crystalbudget/crystall-budget/.env ]; then
    echo "📝 Создание .env файла..."
    cp /opt/crystall-budget/.env /opt/crystalbudget/crystall-budget/.env
fi

# Добавляем таблицу password_reset_tokens в базу данных
echo "🗄️ Добавление таблицы password_reset_tokens..."
sqlite3 /opt/crystalbudget/crystall-budget/budget.db < /opt/crystall-budget/add_password_reset_table.sql

# Перезапускаем сервис
echo "🔄 Перезапуск crystalbudget.service..."
sudo systemctl restart crystalbudget

# Проверяем статус
echo "✅ Проверка статуса сервиса..."
sudo systemctl status crystalbudget --no-pager

echo "🎉 Исправление завершено!"