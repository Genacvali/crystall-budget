# 🚀 Развертывание CrystalBudget с nginx и HTTPS

## Быстрый запуск

### 🆕 Для обновления существующего приложения (с новыми функциями)

```bash
cd /root/crystall-budget

# 1. Остановить сервис
sudo systemctl stop crystalbudget

# 2. Сделать резервную копию базы данных
cp budget.db budget_backup_$(date +%Y%m%d_%H%M%S).db

# 3. Запустить миграцию новых таблиц
python3 migrate_new_tables.py

# 4. Перезапустить сервис
sudo systemctl start crystalbudget

# 5. Проверить статус
sudo systemctl status crystalbudget
```

### Первое развертывание

Если ваш проект уже находится в `/root/crystall-budget`, выполните:

```bash
cd /root/crystall-budget

# Сделать скрипты исполняемыми
chmod +x deploy.sh setup-https.sh

# 1. Базовое развертывание (nginx, systemd, Flask app)
./deploy.sh

# 2. Настройка HTTPS (после настройки DNS)
./setup-https.sh
```

## Пошаговая инструкция

### 1. Базовое развертывание

Скрипт `deploy.sh` автоматически:
- Устанавливает nginx, certbot, Python зависимости
- Создает виртуальное окружение и устанавливает requirements
- Настраивает systemd сервис для автозапуска
- Конфигурирует nginx как reverse proxy
- Генерирует секретный ключ для Flask
- Запускает все сервисы

```bash
./deploy.sh
```

### 2. Настройка домена и DNS

Перед настройкой HTTPS:
1. Убедитесь что у вас есть домен
2. Настройте DNS A-запись: `your-domain.com` → IP вашего сервера
3. Дождитесь распространения DNS (может занять до 24 часов)

Проверить DNS: `nslookup your-domain.com`

### 3. Настройка HTTPS

Скрипт `setup-https.sh` автоматически:
- Обновляет конфигурацию nginx с вашим доменом
- Получает SSL сертификат через Let's Encrypt
- Настраивает автообновление сертификатов
- Конфигурирует файрвол
- Тестирует HTTPS соединение

```bash
./setup-https.sh
```

## Проверка работы

После развертывания проверьте:

```bash
# Статус сервисов
systemctl status crystalbudget nginx

# Логи приложения
journalctl -u crystalbudget -f

# Health check
curl https://your-domain.com/health

# Тест SSL
curl -I https://your-domain.com
```

## Управление сервисом

```bash
# Перезапуск приложения
systemctl restart crystalbudget

# Просмотр логов
journalctl -u crystalbudget -n 50

# Перезагрузка nginx
systemctl reload nginx

# Обновление SSL сертификата
certbot renew
```

## Обновление приложения

```bash
cd /root/crystall-budget

# Остановить приложение
systemctl stop crystalbudget

# Обновить код (git pull или копирование файлов)
git pull

# Обновить зависимости если нужно
.venv/bin/pip install -r requirements.txt

# Запустить приложение
systemctl start crystalbudget
```

## Резервное копирование

```bash
# База данных
cp /root/crystall-budget/budget.db /backup/budget.db.$(date +%Y%m%d)

# Конфигурация
tar -czf /backup/crystalbudget-config.$(date +%Y%m%d).tar.gz \
    /etc/nginx/sites-available/crystalbudget \
    /etc/systemd/system/crystalbudget.service \
    /root/crystall-budget/.secret_key
```

## Мониторинг

### Логи
- Приложение: `/var/log/crystalbudget/` и `journalctl -u crystalbudget`
- Nginx: `/var/log/nginx/crystalbudget.*.log`
- CrystalBudget: `/root/crystall-budget/logs/crystalbudget.log`

### Health Check
- URL: `https://your-domain.com/health`
- Проверяет подключение к базе данных
- Возвращает JSON со статусом

### SSL Мониторинг
```bash
# Информация о сертификатах
certbot certificates

# Тест обновления
certbot renew --dry-run

# Проверка рейтинга SSL
# https://www.ssllabs.com/ssltest/analyze.html?d=your-domain.com
```

## Troubleshooting

### Приложение не запускается
```bash
# Проверить статус
systemctl status crystalbudget

# Посмотреть детальные логи
journalctl -u crystalbudget -n 50

# Проверить что порт 5000 не занят
ss -tlnp | grep :5000
```

### Nginx ошибки
```bash
# Проверить конфигурацию
nginx -t

# Логи ошибок
tail -f /var/log/nginx/error.log
```

### SSL проблемы
```bash
# Проверить статус сертификата
certbot certificates

# Тест обновления
certbot renew --dry-run

# Проверить что DNS настроен
nslookup your-domain.com
```

### База данных
```bash
# Проверить файл базы
ls -la /root/crystall-budget/budget.db

# Проверить права доступа
chmod 644 /root/crystall-budget/budget.db
```

## Безопасность

1. **Файрвол**: Убедитесь что открыты только необходимые порты (22, 80, 443)
2. **SSL**: Регулярно обновляйте сертификаты (автоматически через cron)
3. **Секретный ключ**: Храните `/root/crystall-budget/.secret_key` в безопасности
4. **Обновления**: Регулярно обновляйте систему и зависимости
5. **Логи**: Мониторьте логи на предмет подозрительной активности