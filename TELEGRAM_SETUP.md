# 🤖 Настройка Telegram бота для CrystalBudget

## Быстрый старт

### 1. Создание бота в Telegram

1. Найдите [@BotFather](https://t.me/botfather) в Telegram
2. Отправьте `/newbot`
3. Введите имя бота: `CrystalBudget Bot`
4. Введите username: `crystalbudget_bot` (или другой доступный)
5. Скопируйте токен бота

### 2. Установка зависимостей

```bash
pip install python-telegram-bot
```

### 3. Настройка переменных окружения

```bash
# В .env или export
export TELEGRAM_BOT_TOKEN="8284293072:AAE2LEaJHhOYBvFcDf7cT_B2Y2SlSXQMbOA"
export WEB_URL="https://crystalbudget.net"
export BUDGET_DB="/opt/crystall-budget/budget.db"
```

### 4. Обновление базы данных

Добавьте таблицу `user_telegram` в БД:

```sql
sqlite3 /var/lib/crystalbudget/budget.db

CREATE TABLE IF NOT EXISTS user_telegram (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    telegram_id TEXT UNIQUE NOT NULL,
    telegram_username TEXT,
    telegram_first_name TEXT,
    telegram_last_name TEXT,
    is_verified INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    verified_at TIMESTAMP NULL,
    UNIQUE(user_id)
);

CREATE INDEX IF NOT EXISTS idx_user_telegram_user ON user_telegram(user_id);
CREATE INDEX IF NOT EXISTS idx_user_telegram_telegram_id ON user_telegram(telegram_id);

.quit
```

### 5. Запуск бота

```bash
python telegram_bot.py
```

Или как systemd сервис:

```bash
# Создать файл /etc/systemd/system/crystalbudget-bot.service
sudo nano /etc/systemd/system/crystalbudget-bot.service
```

Содержимое файла:
```ini
[Unit]
Description=CrystalBudget Telegram Bot
After=network.target
Requires=network.target

[Service]
Type=simple
User=crystalbudget
Group=crystalbudget
WorkingDirectory=/opt/crystalbudget/crystall-budget
Environment=TELEGRAM_BOT_TOKEN=ваш_токен
Environment=WEB_URL=https://crystalbudget.net
Environment=BUDGET_DB=/var/lib/crystalbudget/budget.db
ExecStart=/opt/crystalbudget/venv/bin/python telegram_bot.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Запуск:
```bash
sudo systemctl daemon-reload
sudo systemctl enable crystalbudget-bot
sudo systemctl start crystalbudget-bot
sudo systemctl status crystalbudget-bot
```

## Как пользоваться

### Для пользователей:

1. **Связать аккаунт:**
   - Найти бота в Telegram
   - Отправить `/start`
   - Отправить `/link`
   - Ввести email от CrystalBudget

2. **Сбросить пароль:**
   - Отправить `/reset`
   - Нажать на кнопку в сообщении
   - Ввести новый пароль на сайте

### Команды бота:

- `/start` - приветствие и информация
- `/help` - справка по командам  
- `/link` - связать аккаунт с Telegram
- `/reset` - сбросить пароль

## Интеграция с Flask

Добавьте в `app.py` код из файла `telegram_integration.py`:

```python
# Добавить импорты
from datetime import datetime, timedelta
import secrets
import string

# Добавить роуты
@app.route("/reset-password", methods=["GET", "POST"])
def reset_password_telegram():
    # ... код из telegram_integration.py

@app.route("/profile/telegram", methods=["GET", "POST"])  
@login_required
def profile_telegram():
    # ... код из telegram_integration.py
```

## Безопасность

✅ **Что реализовано:**
- Токены истекают через 1 час
- Токены одноразовые
- Связывание только с подтвержденным email
- Логирование всех операций

⚠️ **Рекомендации:**
- Используйте HTTPS для веб-сайта
- Ограничьте доступ к токену бота
- Регулярно проверяйте логи

## Дополнительные возможности

В будущем можно добавить:
- 📊 Уведомления о превышении бюджета
- 🎯 Уведомления о достижении целей
- 📈 Еженедельные отчеты
- 💰 Быстрое добавление расходов через бота

## Отладка

Логи бота:
```bash
journalctl -u crystalbudget-bot -f
```

Проверка БД:
```bash
sqlite3 /var/lib/crystalbudget/budget.db "SELECT * FROM user_telegram;"
```

Тестирование токена:
```bash
curl -X GET "https://api.telegram.org/bot<TOKEN>/getMe"
```