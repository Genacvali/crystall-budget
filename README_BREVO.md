# Настройка Brevo (Sendinblue) для отправки email

## Шаги настройки:

1. **Регистрация в Brevo**
   - Перейдите на https://www.brevo.com/
   - Создайте бесплатный аккаунт (300 emails/день бесплатно)

2. **Настройка SMTP ключа**
   - В панели Brevo перейдите в `Settings` → `SMTP & API`
   - Нажмите `Generate a new SMTP key`
   - Скопируйте сгенерированный ключ

3. **Верификация отправителя**
   - Перейдите в `Senders & IP` → `Senders`
   - Добавьте и подтвердите email-адрес отправителя
   - Используйте этот адрес в `SMTP_FROM_EMAIL`

4. **Создание .env файла**
   ```bash
   cp .env.example .env
   ```

5. **Заполнение параметров**
   ```
   SMTP_SERVER=smtp-relay.brevo.com
   SMTP_PORT=587
   SMTP_USERNAME=ваш_email@domain.com
   SMTP_PASSWORD=ваш_smtp_ключ_из_brevo
   SMTP_FROM_EMAIL=ваш_подтвержденный_email@domain.com
   SECRET_KEY=любая_случайная_строка
   ```

6. **Перезапуск приложения**
   ```bash
   # Остановить текущий процесс (Ctrl+C)
   # Затем запустить с переменными окружения:
   source .env && python app.py
   ```

## Примечания:
- Brevo бесплатно предоставляет 300 emails в день
- SMTP работает на порту 587 с TLS
- Обязательна верификация адреса отправителя
- Для продакшена рекомендуется использовать домен с DKIM/SPF записями