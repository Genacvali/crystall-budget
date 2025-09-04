# Личный бюджет

Простое веб-приложение для управления личным бюджетом, оптимизированное для мобильных устройств (iPhone Safari, iOS 15+).

## Возможности

- **Мобильно-дружественный интерфейс**: крупные кнопки, удобные формы для iPhone Safari
- **Управление категориями**: фиксированные лимиты или проценты от дохода
- **Перенос остатков**: накопительная система между месяцами
- **Быстрое добавление трат**: прямо с главной страницы
- **SQLite база данных**: локальное хранение без внешних зависимостей

## Запуск в режиме разработки

```bash
# Создание виртуального окружения
python -m venv .venv

# Активация окружения
source .venv/bin/activate  # Linux/Mac
# или
.venv\Scripts\activate     # Windows

# Установка зависимостей
pip install -r requirements.txt

# Опциональные переменные окружения
export SECRET_KEY="change-me"           # опционально
export BUDGET_DB="budget.db"            # опционально

# Запуск dev-сервера
python app.py
```

Откройте http://localhost:5000 в браузере.

## Запуск в продакшене (без Docker)

```bash
# Создание и активация виртуального окружения
python -m venv .venv
source .venv/bin/activate

# Установка зависимостей
pip install -r requirements.txt

# Настройка переменных окружения
export SECRET_KEY="prod-secret"
export BUDGET_DB="/var/lib/budget/budget.db"

# Запуск с Gunicorn
gunicorn -w 2 -b 0.0.0.0:5000 app:app
```

## Systemd сервис (опционально)

Создайте файл `/etc/systemd/system/budget.service`:

```ini
[Unit]
Description=Budget Flask app
After=network.target

[Service]
User=www-data
WorkingDirectory=/opt/budget
Environment="SECRET_KEY=prod-secret" "BUDGET_DB=/opt/budget/budget.db"
ExecStart=/opt/budget/.venv/bin/gunicorn -w 2 -b 0.0.0.0:5000 app:app
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

Затем:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now budget.service
```

## Структура приложения

- **Дашборд**: обзор бюджета, быстрое добавление трат
- **Траты**: полный список трат, добавление и удаление
- **Категории**: управление категориями с inline-редактированием
- **Доходы**: установка доходов по месяцам

## База данных

Приложение автоматически создает SQLite базу данных при первом запуске и заполняет её начальными категориями:

- Продукты (30% от дохода)
- Транспорт (5000 руб фикс.)
- Развлечения (15% от дохода)
- Коммунальные (8000 руб фикс.)
- Здоровье (3000 руб фикс.)
- Одежда (10% от дохода)

## Особенности

- **Накопительная система**: неиспользованные лимиты переносятся на следующие месяцы
- **Адаптивный дизайн**: Bootstrap 5 с оптимизацией для мобильных устройств
- **Минимальные зависимости**: только Flask и встроенный sqlite3
- **Автоинициализация**: база данных и начальные данные создаются автоматически