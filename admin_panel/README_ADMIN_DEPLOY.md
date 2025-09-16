# Деплой админской панели на продакшен

## 🚀 Автоматический деплой

```bash
# На продакшен сервере
./deploy_admin.sh
```

Скрипт автоматически:
- Скопирует файлы админской панели
- Настроит systemd сервис
- Сгенерирует безопасные пароли
- Запустит админскую панель
- Подготовит конфигурацию Nginx

## 📋 Ручная установка

### 1. Копирование файлов

```bash
# Копируем основные файлы
sudo cp admin_panel.py /opt/crystalbudget/crystall-budget/
sudo cp -r templates/admin_panel /opt/crystalbudget/crystall-budget/templates/

# Устанавливаем зависимости
source /opt/crystalbudget/venv/bin/activate
pip install python-dotenv
```

### 2. Настройка systemd

```bash
# Копируем сервис
sudo cp admin-panel.service /etc/systemd/system/

# Генерируем пароли
ADMIN_PASSWORD=$(openssl rand -base64 32)
SECRET_KEY=$(openssl rand -hex 32)

# Редактируем сервис
sudo nano /etc/systemd/system/admin-panel.service
# Замените CHANGE_THIS_PASSWORD и CHANGE_THIS_SECRET_KEY

# Запускаем
sudo systemctl daemon-reload
sudo systemctl enable admin-panel
sudo systemctl start admin-panel
```

### 3. Настройка Nginx (опционально)

```bash
# Копируем конфигурацию
sudo cp nginx-admin-panel.conf /etc/nginx/sites-available/admin-crystalbudget

# Редактируем домен
sudo nano /etc/nginx/sites-available/admin-crystalbudget

# Включаем сайт
sudo ln -s /etc/nginx/sites-available/admin-crystalbudget /etc/nginx/sites-enabled/

# Получаем SSL сертификат
sudo certbot --nginx -d admin.вашдомен.com

# Перезагружаем Nginx
sudo nginx -t && sudo systemctl reload nginx
```

## 🔒 Безопасность

### Обязательные настройки:

1. **Смените пароли по умолчанию**
   ```bash
   # В /etc/systemd/system/admin-panel.service
   Environment=ADMIN_PASSWORD=ваш_сложный_пароль
   Environment=ADMIN_SECRET_KEY=ваш_секретный_ключ
   ```

2. **Ограничьте доступ по IP**
   ```nginx
   # В nginx конфигурации раскомментируйте:
   allow 192.168.1.0/24;    # Ваша сеть
   allow ВАШ_IP;            # Ваш IP
   deny all;
   ```

3. **Используйте отдельный поддомен**
   ```
   admin.crystalbudget.net  # Вместо основного домена
   ```

4. **Включите fail2ban** (опционально)
   ```bash
   sudo apt install fail2ban
   # Настройте правила для защиты от брутфорса
   ```

## 🔧 Команды управления

```bash
# Управление сервисом
sudo systemctl start admin-panel     # Запуск
sudo systemctl stop admin-panel      # Остановка
sudo systemctl restart admin-panel   # Перезапуск
sudo systemctl status admin-panel    # Статус

# Просмотр логов
sudo journalctl -u admin-panel -f    # В реальном времени
sudo journalctl -u admin-panel -n 50 # Последние 50 строк

# Обновление админской панели
./deploy_admin.sh                     # Повторный запуск деплоя
```

## 📊 Мониторинг

### Проверка работоспособности:

```bash
# Статус сервиса
systemctl is-active admin-panel

# Проверка порта
ss -tlnp | grep :5001

# Тест доступности
curl -I http://localhost:5001
```

### Логи:

```bash
# Логи приложения
sudo journalctl -u admin-panel --since "1 hour ago"

# Логи Nginx (если используется)
sudo tail -f /var/log/nginx/admin-crystalbudget-access.log
sudo tail -f /var/log/nginx/admin-crystalbudget-error.log
```

## 🔄 Обновление

При обновлении основного приложения:

```bash
# 1. Остановите админскую панель
sudo systemctl stop admin-panel

# 2. Обновите файлы
git pull  # или другой способ обновления

# 3. Скопируйте новые файлы админки
sudo cp admin_panel.py /opt/crystalbudget/crystall-budget/
sudo cp -r templates/admin_panel /opt/crystalbudget/crystall-budget/templates/

# 4. Запустите админскую панель
sudo systemctl start admin-panel
```

## ⚠️ Важные замечания

1. **Администратор ВИДИТ ВСЕ ДАННЫЕ** - доверяйте доступ только проверенным людям
2. **Панель работает на отдельном порту** (5001) - настройте файрвол
3. **SQL консоль очень мощная** - будьте осторожны с запросами
4. **Резервные копии** создавайте перед важными изменениями
5. **Логи ротируются** автоматически через systemd

## 🆘 Устранение проблем

### Админская панель не запускается:
```bash
# Проверьте логи
sudo journalctl -u admin-panel -n 50

# Проверьте права доступа
ls -la /opt/crystalbudget/crystall-budget/budget.db

# Проверьте Python окружение
source /opt/crystalbudget/venv/bin/activate
python -c "import flask, sqlite3, dotenv"
```

### Не работает авторизация:
```bash
# Проверьте переменные окружения
sudo systemctl show admin-panel -p Environment

# Сбросьте пароль через переменные окружения
sudo systemctl edit admin-panel
# Добавьте новые Environment переменные
```

### Ошибки базы данных:
```bash
# Проверьте структуру БД
sqlite3 /opt/crystalbudget/crystall-budget/budget.db ".schema users"

# Добавьте колонку role если нужно
sqlite3 /opt/crystalbudget/crystall-budget/budget.db "ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'user';"
```