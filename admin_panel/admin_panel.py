#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Отдельная админская панель для управления CrystalBudget
Запускается на порту 5001 и предоставляет полный доступ к базе данных
"""

import os
import sqlite3
import secrets
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from werkzeug.security import generate_password_hash
import json

# Конфигурация
app = Flask(__name__, template_folder='templates')
app.secret_key = os.environ.get('ADMIN_SECRET_KEY', 'admin-panel-secret-key-change-me')
DB_PATH = os.environ.get('BUDGET_DB', '../budget.db')

# Простая авторизация админки
ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'admin123')

def get_db():
    """Подключение к базе данных."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def login_required(f):
    def wrapper(*args, **kwargs):
        if 'admin_logged_in' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper

@app.route('/')
@login_required
def index():
    """Главная страница админки."""
    conn = get_db()
    
    # Общая статистика
    stats = {}
    
    # Проверяем наличие колонки role и добавляем если нужно
    try:
        cursor = conn.execute("PRAGMA table_info(users)")
        columns = [col[1] for col in cursor.fetchall()]
        if 'role' not in columns:
            conn.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'user'")
            conn.execute("UPDATE users SET role = 'admin' WHERE id = 1")
            conn.commit()
    except Exception as e:
        print(f"Warning: Could not add role column: {e}")
    
    # Статистика пользователей
    users_data = conn.execute("""
        SELECT 
            COUNT(*) as total_users,
            COUNT(CASE WHEN role = 'admin' THEN 1 END) as admin_users,
            COUNT(CASE WHEN created_at > datetime('now', '-7 days') THEN 1 END) as new_users_week,
            COUNT(CASE WHEN created_at > datetime('now', '-30 days') THEN 1 END) as new_users_month
        FROM users
    """).fetchone()
    
    # Статистика активности (без конфиденциальных сумм)
    activity_data = conn.execute("""
        SELECT 
            COUNT(DISTINCT e.user_id) as active_users,
            COUNT(e.id) as total_expenses,
            COUNT(CASE WHEN e.date > date('now', '-7 days') THEN 1 END) as recent_expenses
        FROM expenses e
    """).fetchone()
    
    # Размер базы данных
    db_size = os.path.getsize(DB_PATH) if os.path.exists(DB_PATH) else 0
    
    # Последние пользователи
    recent_users = conn.execute("""
        SELECT id, email, name, role, created_at
        FROM users 
        ORDER BY created_at DESC 
        LIMIT 5
    """).fetchall()
    
    conn.close()
    
    return render_template('dashboard.html',
                         users_data=users_data,
                         activity_data=activity_data,
                         db_size=db_size,
                         recent_users=recent_users)

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Авторизация в админке."""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            flash('Добро пожаловать в админскую панель!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Неверный логин или пароль', 'error')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    """Выход из админки."""
    session.pop('admin_logged_in', None)
    flash('Вы вышли из админской панели', 'info')
    return redirect(url_for('login'))

@app.route('/users')
@login_required
def users():
    """Управление пользователями."""
    conn = get_db()
    
    search = request.args.get('search', '')
    
    query = """
        SELECT u.id, u.email, u.name, u.role, u.created_at, u.default_currency,
               u.auth_type, u.telegram_id, u.telegram_username,
               COUNT(DISTINCT e.id) as expenses_count,
               COUNT(DISTINCT c.id) as categories_count,
               MAX(e.date) as last_expense_date
        FROM users u
        LEFT JOIN expenses e ON u.id = e.user_id
        LEFT JOIN categories c ON u.id = c.user_id
    """
    
    params = []
    if search:
        query += " WHERE u.email LIKE ? OR u.name LIKE ?"
        params = [f'%{search}%', f'%{search}%']
    
    query += """
        GROUP BY u.id
        ORDER BY u.created_at DESC
    """
    
    users_list = conn.execute(query, params).fetchall()
    conn.close()
    
    return render_template('users.html', 
                         users=users_list, 
                         search=search)

@app.route('/users/<int:user_id>')
@login_required
def user_detail(user_id):
    """Детальная информация о пользователе."""
    conn = get_db()
    
    # Информация о пользователе
    user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    if not user:
        flash('Пользователь не найден', 'error')
        return redirect(url_for('users'))
    
    # Статистика пользователя
    stats = conn.execute("""
        SELECT 
            COUNT(DISTINCT e.id) as expenses_count,
            COUNT(DISTINCT c.id) as categories_count,
            COUNT(DISTINCT i.id) as income_count
        FROM users u
        LEFT JOIN expenses e ON u.id = e.user_id
        LEFT JOIN categories c ON u.id = c.user_id
        LEFT JOIN income_daily i ON u.id = i.user_id
        WHERE u.id = ?
    """, (user_id,)).fetchone()
    
    # Последние расходы (без сумм)
    recent_expenses = conn.execute("""
        SELECT e.date, c.name as category_name, e.note
        FROM expenses e
        JOIN categories c ON e.category_id = c.id
        WHERE e.user_id = ?
        ORDER BY e.date DESC
        LIMIT 10
    """, (user_id,)).fetchall()
    
    # Категории пользователя
    categories = conn.execute("""
        SELECT * FROM categories
        WHERE user_id = ?
        ORDER BY name
    """, (user_id,)).fetchall()
    
    conn.close()
    
    return render_template('user_detail.html',
                         user=user,
                         stats=stats,
                         recent_expenses=recent_expenses,
                         categories=categories)

@app.route('/users/<int:user_id>/reset-password', methods=['POST'])
@login_required
def reset_user_password(user_id):
    """Сброс пароля пользователя."""
    conn = get_db()
    
    user = conn.execute("SELECT email FROM users WHERE id = ?", (user_id,)).fetchone()
    if not user:
        flash('Пользователь не найден', 'error')
        return redirect(url_for('users'))
    
    # Генерируем новый временный пароль
    new_password = secrets.token_urlsafe(12)
    password_hash = generate_password_hash(new_password)
    
    # Обновляем пароль в базе
    conn.execute("UPDATE users SET password_hash = ? WHERE id = ?", 
                (password_hash, user_id))
    conn.commit()
    conn.close()
    
    flash(f'Пароль пользователя {user["email"]} сброшен. Новый пароль: {new_password}', 'success')
    return redirect(url_for('user_detail', user_id=user_id))

@app.route('/users/<int:user_id>/toggle-role', methods=['POST'])
@login_required
def toggle_user_role(user_id):
    """Переключение роли пользователя."""
    conn = get_db()
    
    user = conn.execute("SELECT role, email FROM users WHERE id = ?", (user_id,)).fetchone()
    if not user:
        flash('Пользователь не найден', 'error')
        return redirect(url_for('users'))
    
    new_role = 'user' if user['role'] == 'admin' else 'admin'
    conn.execute("UPDATE users SET role = ? WHERE id = ?", (new_role, user_id))
    conn.commit()
    conn.close()
    
    flash(f'Роль пользователя {user["email"]} изменена на "{new_role}"', 'success')
    return redirect(url_for('user_detail', user_id=user_id))

@app.route('/users/<int:user_id>/delete', methods=['POST'])
@login_required
def delete_user(user_id):
    """Удаление пользователя и всех связанных данных."""
    conn = get_db()
    
    # Проверяем что пользователь существует
    user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    if not user:
        flash('Пользователь не найден', 'error')
        return redirect(url_for('users'))
    
    try:
        # Начинаем транзакцию
        conn.execute("BEGIN TRANSACTION")
        
        # Удаляем связанные данные в правильном порядке (из-за foreign keys)
        
        # 1. Удаляем правила распределения доходов
        conn.execute("DELETE FROM source_category_rules WHERE user_id = ?", (user_id,))
        
        # 2. Удаляем ежедневные доходы
        conn.execute("DELETE FROM income_daily WHERE user_id = ?", (user_id,))
        
        # 3. Удаляем источники доходов
        conn.execute("DELETE FROM income_sources WHERE user_id = ?", (user_id,))
        
        # 4. Удаляем старые доходы
        conn.execute("DELETE FROM income WHERE user_id = ?", (user_id,))
        
        # 5. Удаляем расходы
        conn.execute("DELETE FROM expenses WHERE user_id = ?", (user_id,))
        
        # 6. Удаляем цели сбережений
        try:
            conn.execute("DELETE FROM savings_goals WHERE user_id = ?", (user_id,))
        except sqlite3.OperationalError:
            pass  # Таблица может не существовать
        
        # 7. Удаляем участие в семейных бюджетах
        try:
            conn.execute("DELETE FROM shared_budget_members WHERE user_id = ?", (user_id,))
        except sqlite3.OperationalError:
            pass  # Таблица может не существовать
            
        # 8. Удаляем семейные бюджеты, созданные пользователем
        try:
            conn.execute("DELETE FROM shared_budgets WHERE owner_id = ?", (user_id,))
        except sqlite3.OperationalError:
            pass  # Таблица может не существовать
        
        # 9. Удаляем категории
        conn.execute("DELETE FROM categories WHERE user_id = ?", (user_id,))
        
        # 10. Удаляем переносы бюджета
        try:
            conn.execute("DELETE FROM budget_rollover WHERE user_id = ?", (user_id,))
        except sqlite3.OperationalError:
            pass  # Таблица может не существовать
        
        # 11. Наконец удаляем самого пользователя
        conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
        
        # Подтверждаем транзакцию
        conn.commit()
        
        # Удаляем аватар если есть
        if user.get('avatar_path'):
            avatar_full_path = os.path.join(os.path.dirname(__file__), '..', user['avatar_path'])
            try:
                if os.path.exists(avatar_full_path):
                    os.remove(avatar_full_path)
            except Exception as e:
                print(f"Warning: Could not delete avatar file: {e}")
        
        user_identifier = user.get('email') or user.get('telegram_username') or f"ID:{user['id']}"
        flash(f'Пользователь {user_identifier} и все его данные успешно удалены', 'success')
        
    except Exception as e:
        # Откатываем транзакцию при ошибке
        conn.execute("ROLLBACK")
        flash(f'Ошибка при удалении пользователя: {e}', 'error')
        print(f"Error deleting user {user_id}: {e}")
    
    finally:
        conn.close()
    
    return redirect(url_for('users'))

@app.route('/users/<int:user_id>/migrate-to-telegram', methods=['GET', 'POST'])
@login_required
def migrate_user_to_telegram(user_id):
    """Миграция пользователя с email авторизации на Telegram."""
    conn = get_db()
    
    user = conn.execute("SELECT * FROM users WHERE id = ? AND auth_type = 'email'", (user_id,)).fetchone()
    if not user:
        flash('Пользователь не найден или уже использует Telegram авторизацию', 'error')
        return redirect(url_for('users'))
    
    if request.method == 'POST':
        telegram_id = request.form.get('telegram_id', '').strip()
        telegram_username = request.form.get('telegram_username', '').strip()
        telegram_first_name = request.form.get('telegram_first_name', '').strip()
        telegram_last_name = request.form.get('telegram_last_name', '').strip()
        
        if not telegram_id:
            flash('Telegram ID обязателен для миграции', 'error')
            return render_template('migrate_user.html', user=user)
        
        try:
            # Проверяем что такой telegram_id не используется
            existing = conn.execute("SELECT id FROM users WHERE telegram_id = ?", (telegram_id,)).fetchone()
            if existing:
                flash('Этот Telegram ID уже используется другим пользователем', 'error')
                return render_template('migrate_user.html', user=user)
            
            # Обновляем пользователя
            conn.execute("""
                UPDATE users 
                SET auth_type = 'telegram', 
                    telegram_id = ?, 
                    telegram_username = ?, 
                    telegram_first_name = ?, 
                    telegram_last_name = ?
                WHERE id = ?
            """, (telegram_id, telegram_username, telegram_first_name, telegram_last_name, user_id))
            
            conn.commit()
            conn.close()
            
            flash(f'Пользователь {user["email"]} успешно мигрирован на Telegram авторизацию', 'success')
            return redirect(url_for('user_detail', user_id=user_id))
            
        except Exception as e:
            flash(f'Ошибка миграции: {e}', 'error')
            conn.close()
            return render_template('migrate_user.html', user=user)
    
    conn.close()
    return render_template('migrate_user.html', user=user)

@app.route('/database')
@login_required
def database():
    """Обзор базы данных."""
    conn = get_db()
    
    # Список таблиц
    tables = conn.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' 
        ORDER BY name
    """).fetchall()
    
    # Информация о каждой таблице
    tables_info = []
    for table in tables:
        table_name = table['name']
        
        # Количество записей
        count = conn.execute(f"SELECT COUNT(*) as count FROM {table_name}").fetchone()
        
        # Структура таблицы
        structure = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
        
        # Размер таблицы (приблизительно)
        sample = conn.execute(f"SELECT * FROM {table_name} LIMIT 1").fetchone()
        
        tables_info.append({
            'name': table_name,
            'count': count['count'],
            'columns': len(structure),
            'structure': structure,
            'sample': sample
        })
    
    conn.close()
    
    return render_template('database.html', tables_info=tables_info)

@app.route('/sql', methods=['GET', 'POST'])
@login_required
def sql_console():
    """SQL консоль."""
    result = None
    error = None
    query = request.form.get('query', '') if request.method == 'POST' else ''
    
    if request.method == 'POST' and query.strip():
        conn = get_db()
        try:
            cursor = conn.execute(query)
            
            if query.strip().upper().startswith(('SELECT', 'PRAGMA')):
                columns = [desc[0] for desc in cursor.description] if cursor.description else []
                rows = cursor.fetchall()
                result = {
                    'type': 'select',
                    'columns': columns,
                    'rows': rows,
                    'count': len(rows)
                }
            else:
                conn.commit()
                result = {
                    'type': 'modify',
                    'message': f'Запрос выполнен успешно. Затронуто строк: {cursor.rowcount}'
                }
        except Exception as e:
            error = str(e)
        finally:
            conn.close()
    
    return render_template('sql.html',
                         query=query,
                         result=result,
                         error=error)

@app.route('/backup')
@login_required
def backup():
    """Создание резервной копии."""
    try:
        backup_name = f"budget_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        backup_path = f"backups/{backup_name}"
        
        # Создаем папку для бэкапов
        os.makedirs('backups', exist_ok=True)
        
        # Копируем базу данных
        conn = get_db()
        backup_conn = sqlite3.connect(backup_path)
        conn.backup(backup_conn)
        backup_conn.close()
        conn.close()
        
        flash(f'Резервная копия создана: {backup_name}', 'success')
    except Exception as e:
        flash(f'Ошибка создания резервной копии: {e}', 'error')
    
    return redirect(url_for('index'))

@app.route('/api/stats')
@login_required
def api_stats():
    """API для получения статистики."""
    conn = get_db()
    
    # Статистика по дням (последние 30 дней)
    daily_stats = conn.execute("""
        SELECT 
            date(e.date) as day,
            COUNT(e.id) as expenses_count,
            SUM(e.amount) as total_amount
        FROM expenses e
        WHERE e.date >= date('now', '-30 days')
        GROUP BY date(e.date)
        ORDER BY day
    """).fetchall()
    
    # Топ категорий по тратам
    top_categories = conn.execute("""
        SELECT 
            c.name,
            SUM(e.amount) as total
        FROM expenses e
        JOIN categories c ON e.category_id = c.id
        WHERE e.date >= date('now', '-30 days')
        GROUP BY c.id, c.name
        ORDER BY total DESC
        LIMIT 10
    """).fetchall()
    
    conn.close()
    
    return jsonify({
        'daily_stats': [dict(row) for row in daily_stats],
        'top_categories': [dict(row) for row in top_categories]
    })

if __name__ == '__main__':
    # Определяем режим работы
    debug_mode = os.environ.get('FLASK_ENV') == 'development'
    
    if debug_mode:
        print("🔧 Запуск админской панели CrystalBudget (DEV)")
        print(f"📊 База данных: {DB_PATH}")
        print(f"👤 Логин: {ADMIN_USERNAME}")
        print(f"🔒 Пароль: {ADMIN_PASSWORD}")
        print("🌐 Доступ: http://localhost:5001")
    else:
        print("🚀 Админская панель CrystalBudget запущена (PROD)")
    
    app.run(host='0.0.0.0', port=5001, debug=debug_mode)