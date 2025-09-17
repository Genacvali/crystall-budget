#!/usr/bin/env python3
"""
Telegram бот для CrystalBudget - сброс пароля и уведомления
"""

import os
import sqlite3
import secrets
import string
from datetime import datetime, timedelta
import asyncio
import logging
from typing import Optional

try:
    from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
    from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
    from werkzeug.security import generate_password_hash
except ImportError:
    print("❌ Нужно установить python-telegram-bot:")
    print("pip install python-telegram-bot")
    exit(1)

# Настройки
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
DB_PATH = os.environ.get("BUDGET_DB", "/var/lib/crystalbudget/budget.db")
WEB_URL = os.environ.get("WEB_URL", "https://crystalbudget.net")

if not BOT_TOKEN:
    print("❌ Установите переменную окружения TELEGRAM_BOT_TOKEN")
    exit(1)

# Логирование
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class DatabaseManager:
    """Менеджер базы данных"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
    
    def get_connection(self):
        """Получить соединение с БД"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def find_user_by_email(self, email: str) -> Optional[dict]:
        """Найти пользователя по email"""
        conn = self.get_connection()
        try:
            cursor = conn.execute(
                "SELECT id, email, name FROM users WHERE email = ?", 
                (email.lower(),)
            )
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()
    
    def get_user_telegram(self, user_id: int) -> Optional[dict]:
        """Получить Telegram связь пользователя"""
        conn = self.get_connection()
        try:
            cursor = conn.execute(
                "SELECT * FROM user_telegram WHERE user_id = ?", 
                (user_id,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()
    
    def link_telegram(self, user_id: int, telegram_id: str, telegram_data: dict):
        """Связать пользователя с Telegram"""
        conn = self.get_connection()
        try:
            conn.execute("""
                INSERT OR REPLACE INTO user_telegram 
                (user_id, telegram_id, telegram_username, telegram_first_name, 
                 telegram_last_name, is_verified, verified_at)
                VALUES (?, ?, ?, ?, ?, 1, CURRENT_TIMESTAMP)
            """, (
                user_id, telegram_id, 
                telegram_data.get('username'),
                telegram_data.get('first_name'),
                telegram_data.get('last_name')
            ))
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error linking telegram: {e}")
            return False
        finally:
            conn.close()
    
    def create_password_reset_token(self, user_id: int) -> str:
        """Создать токен сброса пароля"""
        token = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(32))
        expires_at = datetime.now() + timedelta(hours=1)  # Токен действует 1 час
        
        conn = self.get_connection()
        try:
            conn.execute("""
                INSERT INTO password_reset_tokens 
                (user_id, token, expires_at)
                VALUES (?, ?, ?)
            """, (user_id, token, expires_at.isoformat()))
            conn.commit()
            return token
        finally:
            conn.close()
    
    def reset_password_with_token(self, token: str, new_password: str) -> bool:
        """Сбросить пароль по токену"""
        conn = self.get_connection()
        try:
            # Проверяем токен
            cursor = conn.execute("""
                SELECT user_id FROM password_reset_tokens 
                WHERE token = ? AND expires_at > ? AND used = 0
            """, (token, datetime.now().isoformat()))
            
            row = cursor.fetchone()
            if not row:
                return False
            
            user_id = row['user_id']
            password_hash = generate_password_hash(new_password)
            
            # Обновляем пароль
            conn.execute(
                "UPDATE users SET password_hash = ? WHERE id = ?",
                (password_hash, user_id)
            )
            
            # Помечаем токен как использованный
            conn.execute(
                "UPDATE password_reset_tokens SET used = 1 WHERE token = ?",
                (token,)
            )
            
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error resetting password: {e}")
            return False
        finally:
            conn.close()

# Глобальный менеджер БД
db = DatabaseManager(DB_PATH)

# Временное хранилище для процесса связывания
user_sessions = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start"""
    user = update.effective_user
    
    await update.message.reply_text(
        f"👋 Привет, {user.first_name}!\n\n"
        f"🔐 Я бот CrystalBudget для сброса пароля.\n\n"
        f"📝 Доступные команды:\n"
        f"/link - связать аккаунт с Telegram\n"
        f"/reset - сбросить пароль\n"
        f"/help - помощь"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /help"""
    await update.message.reply_text(
        "🆘 **Помощь CrystalBudget Bot**\n\n"
        "🔗 **/link** - связать ваш аккаунт CrystalBudget с Telegram\n"
        "🔐 **/reset** - сбросить пароль (нужна предварительная связка)\n"
        "❓ **/help** - показать эту справку\n\n"
        f"🌐 Сайт: {WEB_URL}\n"
        "📧 Поддержка: @support",
        parse_mode='Markdown'
    )

async def link_account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /link для связывания аккаунта"""
    telegram_id = str(update.effective_user.id)
    
    await update.message.reply_text(
        "🔗 **Связывание аккаунта с Telegram**\n\n"
        "📧 Введите email вашего аккаунта CrystalBudget:",
        parse_mode='Markdown'
    )
    
    # Сохраняем состояние пользователя
    user_sessions[telegram_id] = {'state': 'waiting_email'}

async def reset_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /reset для сброса пароля"""
    telegram_id = str(update.effective_user.id)
    
    # Проверяем, связан ли аккаунт
    conn = db.get_connection()
    try:
        cursor = conn.execute("""
            SELECT u.id, u.email, u.name 
            FROM users u
            JOIN user_telegram ut ON u.id = ut.user_id
            WHERE ut.telegram_id = ? AND ut.is_verified = 1
        """, (telegram_id,))
        
        user = cursor.fetchone()
        if not user:
            await update.message.reply_text(
                "❌ **Аккаунт не связан**\n\n"
                "Сначала свяжите ваш аккаунт командой /link",
                parse_mode='Markdown'
            )
            return
        
        # Создаем токен сброса
        token = db.create_password_reset_token(user['id'])
        reset_url = f"{WEB_URL}/reset-password?token={token}"
        
        keyboard = [[InlineKeyboardButton("🔐 Сбросить пароль", url=reset_url)]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"🔐 **Сброс пароля**\n\n"
            f"👤 Аккаунт: {user['email']}\n"
            f"⏰ Ссылка действует 1 час\n\n"
            f"Нажмите кнопку ниже для сброса пароля:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
    finally:
        conn.close()

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка текстовых сообщений"""
    telegram_id = str(update.effective_user.id)
    text = update.message.text
    
    if telegram_id not in user_sessions:
        await update.message.reply_text(
            "❓ Используйте команды:\n"
            "/start - начать\n"
            "/link - связать аккаунт\n" 
            "/reset - сбросить пароль"
        )
        return
    
    session = user_sessions[telegram_id]
    
    if session['state'] == 'waiting_email':
        # Проверяем email
        user = db.find_user_by_email(text)
        if not user:
            await update.message.reply_text(
                "❌ **Пользователь не найден**\n\n"
                "Проверьте правильность email или зарегистрируйтесь на сайте",
                parse_mode='Markdown'
            )
            del user_sessions[telegram_id]
            return
        
        # Связываем аккаунт
        telegram_data = {
            'username': update.effective_user.username,
            'first_name': update.effective_user.first_name,
            'last_name': update.effective_user.last_name
        }
        
        if db.link_telegram(user['id'], telegram_id, telegram_data):
            await update.message.reply_text(
                f"✅ **Аккаунт успешно связан!**\n\n"
                f"👤 {user['name']} ({user['email']})\n"
                f"📱 Telegram: @{update.effective_user.username or 'без username'}\n\n"
                f"Теперь вы можете использовать /reset для сброса пароля",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                "❌ **Ошибка связывания**\n\n"
                "Попробуйте позже или обратитесь в поддержку",
                parse_mode='Markdown'
            )
        
        del user_sessions[telegram_id]

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ошибок"""
    logger.error(f"Exception while handling an update: {context.error}")

def main():
    """Запуск бота"""
    print(f"🤖 Запуск CrystalBudget Telegram Bot...")
    print(f"📁 База данных: {DB_PATH}")
    print(f"🌐 Веб-сайт: {WEB_URL}")
    
    # Создаем приложение
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Добавляем обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("link", link_account))
    application.add_handler(CommandHandler("reset", reset_password))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Обработчик ошибок
    application.add_error_handler(error_handler)
    
    # Запускаем бота
    print("✅ Бот запущен и готов к работе!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()