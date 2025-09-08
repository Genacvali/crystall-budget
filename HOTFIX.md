# 🚑 ЭКСТРЕННОЕ ИСПРАВЛЕНИЕ PRODUCTION

## 🔥 Проблема
```
AttributeError: 'sqlite3.Row' object has no attribute 'get'
```

## ⚡ Быстрое исправление

На production сервере выполните:

```bash
# Загрузите исправленные файлы
scp -r app/ crystal@your-server:/opt/crystalbudget/crystall-budget/
scp -r deploy/ crystal@your-server:/opt/crystalbudget/crystall-budget/
scp wsgi.py crystal@your-server:/opt/crystalbudget/crystall-budget/

# Примените полное исправление
sudo ./deploy/hotfix_complete.sh
```

## 🛠 Что исправляется

### 1. sqlite3.Row.get() → правильный доступ
```python
# Неправильно (вызывает ошибку)
session['theme'] = user.get('theme', 'light')

# Правильно  
session['theme'] = user['theme'] if 'theme' in user.keys() else 'light'
```

### 2. Gunicorn точка входа
```ini
# wsgi:app вместо app:app
ExecStart=... wsgi:app
```

### 3. Права доступа и структура модулей

## ✅ После исправления

Сервис должен:
- ✅ Запуститься без ошибок
- ✅ Принимать HTTP запросы  
- ✅ Обрабатывать логин/регистрацию
- ✅ Работать с валютной конвертацией

## 🔍 Проверка результата

```bash
# Статус сервиса
sudo systemctl status crystalbudget

# Логи в реальном времени
sudo journalctl -u crystalbudget -f

# HTTP тест
curl -I http://localhost:5000
```

## 🆘 Если не помогло

1. Проверьте структуру модулей:
```bash
ls -la /opt/crystalbudget/crystall-budget/app/
```

2. Тест импорта:
```bash
sudo -u crystal python3 -c "from app import create_app; print('OK')"
```

3. Откат к старой версии:
```bash
sudo systemctl stop crystalbudget
# восстановить старый app.py
sudo systemctl start crystalbudget  
```

## 📞 Техническая поддержка

Все скрипты создают резервные копии и логируют действия для отката при необходимости.