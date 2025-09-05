# Настройка продакшн-сервера с nginx и HTTPS

## 1. Подготовка сервера

### Установка зависимостей
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install nginx python3 python3-pip python3-venv certbot python3-certbot-nginx

# CentOS/RHEL
sudo yum install nginx python3 python3-pip certbot python3-certbot-nginx
```

## 2. Развертывание приложения

### Создание пользователя и директорий
```bash
sudo useradd -r -s /bin/false crystalbudget
sudo mkdir -p /opt/crystalbudget
sudo mkdir -p /var/log/crystalbudget
sudo chown crystalbudget:crystalbudget /var/log/crystalbudget
```

### Копирование файлов
```bash
# Скопировать файлы приложения в /opt/crystalbudget/
sudo cp -r . /opt/crystalbudget/
sudo chown -R crystalbudget:crystalbudget /opt/crystalbudget
cd /opt/crystalbudget

# Создание виртуального окружения
sudo -u crystalbudget python3 -m venv .venv
sudo -u crystalbudget .venv/bin/pip install -r requirements.txt
```

## 3. Настройка systemd

### Установка сервиса
```bash
sudo cp crystalbudget.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable crystalbudget
```

### Настройка переменных окружения
Отредактируйте `/etc/systemd/system/crystalbudget.service`:
- Замените `your-production-secret-key-change-this` на надежный секретный ключ
- При необходимости измените пути и параметры

### Запуск сервиса
```bash
sudo systemctl start crystalbudget
sudo systemctl status crystalbudget
```

## 4. Настройка nginx

### Установка конфигурации
```bash
sudo cp nginx-crystalbudget.conf /etc/nginx/sites-available/crystalbudget
```

### Редактирование конфигурации
Отредактируйте `/etc/nginx/sites-available/crystalbudget`:
- Замените `your-domain.com` на ваш домен
- Убедитесь что пути к статическим файлам корректны

### Активация сайта
```bash
sudo ln -s /etc/nginx/sites-available/crystalbudget /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

## 5. Настройка HTTPS с certbot

### Получение сертификата
```bash
# Остановить nginx временно
sudo systemctl stop nginx

# Получить сертификат (замените your-domain.com)
sudo certbot certonly --standalone -d your-domain.com -d www.your-domain.com

# Запустить nginx обратно
sudo systemctl start nginx
```

### Автоматическая настройка nginx
```bash
# Certbot автоматически настроит nginx конфигурацию
sudo certbot --nginx -d your-domain.com -d www.your-domain.com
```

### Проверка автообновления
```bash
sudo certbot renew --dry-run
```

## 6. Настройка файрвола (UFW)

```bash
sudo ufw allow 'Nginx Full'
sudo ufw allow ssh
sudo ufw enable
```

## 7. Проверка работы

### Проверка сервисов
```bash
sudo systemctl status crystalbudget
sudo systemctl status nginx
sudo certbot certificates
```

### Проверка логов
```bash
# Логи приложения
sudo journalctl -u crystalbudget -f

# Логи nginx
sudo tail -f /var/log/nginx/crystalbudget.access.log
sudo tail -f /var/log/nginx/crystalbudget.error.log

# Логи CrystalBudget
sudo tail -f /var/log/crystalbudget/error.log
```

### Тестирование HTTPS
- Откройте https://your-domain.com в браузере
- Проверьте что редирект с HTTP работает
- Проверьте SSL рейтинг на https://www.ssllabs.com/ssltest/

## 8. Обслуживание

### Обновление приложения
```bash
cd /opt/crystalbudget
sudo systemctl stop crystalbudget
sudo -u crystalbudget git pull  # или копирование новых файлов
sudo -u crystalbudget .venv/bin/pip install -r requirements.txt
sudo systemctl start crystalbudget
```

### Резервное копирование
```bash
# База данных
sudo cp /opt/crystalbudget/budget.db /backup/budget.db.$(date +%Y%m%d)

# Конфигурация
sudo tar -czf /backup/crystalbudget-config.$(date +%Y%m%d).tar.gz \
    /etc/nginx/sites-available/crystalbudget \
    /etc/systemd/system/crystalbudget.service \
    /etc/letsencrypt/live/your-domain.com/
```