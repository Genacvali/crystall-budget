# 🤖 Настройка Telegram авторизации для CrystalBudget

## Быстрый старт

### 1. Создание бота в Telegram

1. Найдите [@BotFather](https://t.me/botfather) в Telegram
2. Отправьте `/newbot`
3. Введите имя бота: `CrystalBudget Auth Bot`
4. Введите username: `crystalbudget_bot` (или другой доступный)
5. Скопируйте токен бота (например: `1234567890:ABCdefGhIJKlmNoPQRsTUVwxyZ`)

### 2. Настройка домена бота

1. В [@BotFather](https://t.me/botfather) отправьте `/setdomain`
2. Выберите вашего бота
3. Введите ваш домен: `https://yourdomain.com`

### 3. Настройка переменных окружения

Добавьте в `.env` файл или экспортируйте переменные:

```bash
# Токен Telegram бота для авторизации
TELEGRAM_BOT_TOKEN="1234567890:ABCdefGhIJKlmNoPQRsTUVwxyZ"

# Базовый URL сайта (используется в Telegram Widget)
WEB_URL="https://yourdomain.com"
```

### 4. Обновление HTML шаблонов

В файлах `templates/login.html` и `templates/register.html` замените:

```javascript
script.setAttribute('data-telegram-login', 'crystalbudget_bot');
```

На ваш username бота:

```javascript
script.setAttribute('data-telegram-login', 'your_bot_username');
```

### 5. Миграция базы данных

Выполните миграцию для добавления поддержки Telegram авторизации:

```bash
python migrate_telegram_auth.py
```

## Структура авторизации

### Email авторизация
- Традиционный вход по email + пароль
- Хранится в полях `email`, `password_hash`
- Значение `auth_type = 'email'`

### Telegram авторизация
- OAuth через Telegram Login Widget
- Хранится в полях `telegram_id`, `telegram_username`, `telegram_first_name`, `telegram_last_name`
- Значение `auth_type = 'telegram'`
- Проверка подлинности через HMAC-SHA256

### Миграция пользователей

Админ панель поддерживает миграцию пользователей с email на Telegram авторизацию:

1. Войдите в админ панель на порту 5001
2. Найдите пользователя с `auth_type = 'email'`
3. Нажмите "Мигрировать на Telegram"
4. Введите данные Telegram пользователя
5. Пользователь сможет войти только через Telegram

## Безопасность

### Валидация Telegram данных

Приложение проверяет подлинность данных от Telegram используя:
- HMAC-SHA256 подпись
- Secret key на основе bot token
- Проверка всех параметров авторизации

### Конфигурация Widget

Telegram Login Widget настроен с параметрами:
- `data-auth-url` - URL для callback после авторизации
- `data-request-access` - запрос разрешения на запись
- `data-lang="ru"` - русский язык интерфейса

## Troubleshooting

### Ошибка "Invalid domain"
- Проверьте что домен правильно настроен в BotFather
- Убедитесь что используете HTTPS (HTTP не поддерживается)

### Ошибка авторизации Telegram
- Проверьте что `TELEGRAM_BOT_TOKEN` установлен правильно
- Убедитесь что username бота совпадает в коде

### База данных не мигрирована
```bash
python migrate_telegram_auth.py
```

### Отсутствуют новые колонки
```sql
-- Проверить структуру таблицы users
.schema users

-- Должны быть колонки:
-- telegram_id TEXT
-- telegram_username TEXT  
-- telegram_first_name TEXT
-- telegram_last_name TEXT
-- auth_type TEXT DEFAULT 'email'
```

## Тестирование

1. Откройте страницу регистрации
2. Нажмите кнопку "Log in with Telegram"
3. Авторизуйтесь в Telegram
4. Проверьте что пользователь создан с `auth_type = 'telegram'`
5. Повторите для страницы входа

Готово! Теперь CrystalBudget поддерживает авторизацию через Telegram 🎉