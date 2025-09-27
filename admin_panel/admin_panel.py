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
from werkzeug.utils import secure_filename
import json

# Конфигурация
app = Flask(__name__, template_folder='templates')
app.secret_key = os.environ.get('ADMIN_SECRET_KEY', 'admin-panel-secret-key-change-me')
DB_PATH = os.environ.get('BUDGET_DB', '../instance/budget.db')

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

def ensure_schema_compatibility():
    """Ensure the restored DB has columns required by the current app version.
    
    Returns:
        list[str]: List of actions performed in the form 'table.column'
    """
    actions = []
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    def _table_exists(cur, name: str) -> bool:
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (name,))
        return cur.fetchone() is not None

    def _columns(cur, table: str) -> set:
        cur.execute(f"PRAGMA table_info({table})")
        return {row[1] for row in cur.fetchall()}

    def _add_if_missing(cur, table: str, col_name: str, col_def: str):
        cols = _columns(cur, table)
        if col_name not in cols:
            cur.execute(f"ALTER TABLE {table} ADD COLUMN {col_def}")
            actions.append(f"{table}.{col_name}")

    try:
        # users table required columns (for modern app expectations)
        if _table_exists(cur, 'users'):
            users_defs = [
                ('theme', "theme TEXT DEFAULT 'light'"),
                ('currency', "currency TEXT DEFAULT 'RUB'"),
                ('timezone', "timezone TEXT DEFAULT 'UTC'"),
                ('locale', "locale TEXT DEFAULT 'ru'"),
                ('default_currency', "default_currency TEXT DEFAULT 'RUB'"),
                ('avatar_path', "avatar_path TEXT"),
                ('role', "role TEXT DEFAULT 'user'"),
            ]
            for name, definition in users_defs:
                _add_if_missing(cur, 'users', name, definition)

        # currency columns for expenses/income tables if missing
        for table in ['expenses', 'income', 'income_daily']:
            if _table_exists(cur, table):
                _add_if_missing(cur, table, 'currency', "currency TEXT DEFAULT 'RUB'")

        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    return actions

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
import re
from werkzeug.security import generate_password_hash

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

def _norm_email(s: str) -> str:
    return (s or "").strip().lower()

def _valid_email(s: str) -> bool:
    return bool(EMAIL_RE.match(s or ""))

@app.route('/users/<int:user_id>/link-email', methods=['GET', 'POST'])
@login_required
def link_email(user_id):
    """Привязать/обновить email у существующего пользователя (обычно TG-аккаунт)."""
    conn = get_db()
    user = conn.execute("SELECT id, email, name, auth_type, telegram_id, telegram_username FROM users WHERE id = ?", (user_id,)).fetchone()
    if not user:
        conn.close()
        flash('Пользователь не найден', 'error')
        return redirect(url_for('users'))

    generated_password = None  # отобразим один раз после обновления

    if request.method == 'POST':
        new_email = _norm_email(request.form.get('email'))
        make_primary = request.form.get('make_primary') == 'on'
        pwd_mode = request.form.get('pwd_mode', 'generate')  # generate | manual | keep

        # валидация email
        if not _valid_email(new_email):
            flash('Некорректный email', 'error')
            conn.close()
            return render_template('link_email.html', user=user)

        # уникальность email
        exists = conn.execute(
            "SELECT id FROM users WHERE lower(email)=lower(?) AND id<>?",
            (new_email, user_id)
        ).fetchone()
        if exists:
            flash('Такой email уже используется другим пользователем', 'error')
            conn.close()
            return render_template('link_email.html', user=user)

        # решаем, менять ли пароль
        password_hash = None
        if pwd_mode == 'generate':
            import secrets
            generated_password = secrets.token_urlsafe(12)
            password_hash = generate_password_hash(generated_password)
        elif pwd_mode == 'manual':
            p1 = (request.form.get('password') or '').strip()
            p2 = (request.form.get('password_confirm') or '').strip()
            if len(p1) < 6:
                flash('Пароль должен быть не короче 6 символов', 'error')
                conn.close()
                return render_template('link_email.html', user=user)
            if p1 != p2:
                flash('Пароли не совпадают', 'error')
                conn.close()
                return render_template('link_email.html', user=user)
            password_hash = generate_password_hash(p1)
        else:
            # keep — не трогаем password_hash
            pass

        # обновляем
        try:
            if password_hash is not None and make_primary:
                conn.execute(
                    "UPDATE users SET email=?, password_hash=?, auth_type='email' WHERE id=?",
                    (new_email, password_hash, user_id)
                )
            elif password_hash is not None:
                conn.execute(
                    "UPDATE users SET email=?, password_hash=? WHERE id=?",
                    (new_email, password_hash, user_id)
                )
            elif make_primary:
                conn.execute(
                    "UPDATE users SET email=?, auth_type='email' WHERE id=?",
                    (new_email, user_id)
                )
            else:
                conn.execute(
                    "UPDATE users SET email=? WHERE id=?",
                    (new_email, user_id)
                )
            conn.commit()
        except Exception as e:
            conn.close()
            flash(f'Ошибка обновления: {e}', 'error')
            return render_template('link_email.html', user=user)

        conn.close()

        if generated_password:
            # показываем временный пароль один раз
            flash(f'Email привязан. Временный пароль: {generated_password}', 'success')
        else:
            flash('Email привязан', 'success')

        return redirect(url_for('user_detail', user_id=user_id))

    # GET
    conn.close()
    return render_template('link_email.html', user=user)

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
    conn = get_db()

    row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    if not row:
        flash('Пользователь не найден', 'error')
        return redirect(url_for('users'))

    user = dict(row)  # теперь можно безопасно user.get(...)
    try:
        # Явно открываем транзакцию
        conn.execute("BEGIN")

        # 1. Связанные данные
        conn.execute("DELETE FROM source_category_rules WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM income_daily WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM income_sources WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM income WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM expenses WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM categories WHERE user_id = ?", (user_id,))

        # Опциональные таблицы
        try: conn.execute("DELETE FROM savings_goals WHERE user_id = ?", (user_id,))
        except sqlite3.OperationalError: pass

        try: conn.execute("DELETE FROM shared_budget_members WHERE user_id = ?", (user_id,))
        except sqlite3.OperationalError: pass

        # В схеме поле называется creator_id
        try: conn.execute("DELETE FROM shared_budgets WHERE creator_id = ?", (user_id,))
        except sqlite3.OperationalError: pass

        try: conn.execute("DELETE FROM budget_rollover WHERE user_id = ?", (user_id,))
        except sqlite3.OperationalError: pass

        # 2. Сам пользователь
        conn.execute("DELETE FROM users WHERE id = ?", (user_id,))

        # 3. Фиксируем изменения в БД
        conn.commit()

    except Exception as e:
        # Откатываем только если есть незавершённая транзакция
        if conn.in_transaction:
            conn.rollback()
        conn.close()
        flash(f'Ошибка при удалении пользователя: {e}', 'error')
        return redirect(url_for('users'))

    # 4. Удаляем аватар на диске (не влияет на БД)
    avatar_path = user.get('avatar_path')
    if avatar_path:
        avatar_full_path = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', avatar_path))
        try:
            if os.path.exists(avatar_full_path):
                os.remove(avatar_full_path)
        except Exception as e:
            print(f"Warning: Could not delete avatar file: {e}")

    user_identifier = user.get('email') or user.get('telegram_username') or f"ID:{user.get('id')}"
    conn.close()
    flash(f'Пользователь {user_identifier} и все его данные успешно удалены', 'success')
    return redirect(url_for('users'))

@app.route('/users/<int:user_id>/migrate-to-telegram', methods=['GET', 'POST'])
@login_required
def migrate_user_to_telegram(user_id):
    """Миграция пользователя с email авторизации на Telegram."""
    conn = get_db()
    
    user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    if not user:
        flash('Пользователь не найден', 'error')
        return redirect(url_for('users'))
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'link_telegram':
            # Привязка Telegram к существующему email аккаунту
            telegram_id = request.form.get('telegram_id', '').strip()
            telegram_username = request.form.get('telegram_username', '').strip()
            telegram_first_name = request.form.get('telegram_first_name', '').strip()
            telegram_last_name = request.form.get('telegram_last_name', '').strip()
            telegram_photo_url = request.form.get('telegram_photo_url', '').strip()
            
            if not telegram_id:
                flash('Telegram ID обязателен', 'error')
                return render_template('migrate_user.html', user=user)
            
            try:
                # Проверяем что такой telegram_id не используется
                existing = conn.execute("SELECT id FROM users WHERE telegram_id = ? AND id != ?", 
                                       (telegram_id, user_id)).fetchone()
                if existing:
                    flash('Этот Telegram ID уже используется другим пользователем', 'error')
                    return render_template('migrate_user.html', user=user)
                
                # Привязываем Telegram к аккаунту (не меняем auth_type)
                conn.execute("""
                    UPDATE users 
                    SET telegram_id = ?, 
                        telegram_username = ?, 
                        telegram_first_name = ?, 
                        telegram_last_name = ?,
                        telegram_photo_url = ?
                    WHERE id = ?
                """, (telegram_id, telegram_username, telegram_first_name, 
                     telegram_last_name, telegram_photo_url, user_id))
                
                conn.commit()
                flash(f'Telegram аккаунт успешно привязан к пользователю {user["email"]}', 'success')
                
            except Exception as e:
                flash(f'Ошибка привязки: {e}', 'error')
                
        elif action == 'switch_to_telegram':
            # Переключение на Telegram как основной способ авторизации
            if not user['telegram_id']:
                flash('Сначала привяжите Telegram аккаунт', 'error')
            else:
                try:
                    conn.execute("UPDATE users SET auth_type = 'telegram' WHERE id = ?", (user_id,))
                    conn.commit()
                    flash(f'Пользователь переключен на Telegram авторизацию', 'success')
                except Exception as e:
                    flash(f'Ошибка переключения: {e}', 'error')
                    
        elif action == 'switch_to_email':
            # Переключение обратно на email авторизацию
            if not user['email'] or not user['password_hash']:
                flash('У пользователя нет email/пароля для переключения', 'error')
            else:
                try:
                    conn.execute("UPDATE users SET auth_type = 'email' WHERE id = ?", (user_id,))
                    conn.commit()
                    flash(f'Пользователь переключен на email авторизацию', 'success')
                except Exception as e:
                    flash(f'Ошибка переключения: {e}', 'error')
        
        # Обновляем данные пользователя после изменений
        user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    
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

@app.route('/restore', methods=['POST'])
@login_required
def restore():
    """Восстановление базы данных из загруженного бэкапа."""
    file = request.files.get('backup_file')
    if not file or file.filename == '':
        flash('Не выбран файл для загрузки', 'error')
        return redirect(url_for('database'))

    try:
        filename = secure_filename(file.filename)
        allowed_exts = ('.db', '.sqlite', '.sqlite3', '.backup', '.bak')
        if not filename.lower().endswith(allowed_exts):
            flash('Недопустимый тип файла. Разрешены: .db, .sqlite, .sqlite3, .backup, .bak', 'error')
            return redirect(url_for('database'))

        os.makedirs('backups/uploads', exist_ok=True)
        upload_path = os.path.join('backups', 'uploads', f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}")
        file.save(upload_path)

        # Проверяем целостность загруженной БД
        src_conn = sqlite3.connect(upload_path)
        cur = src_conn.execute("PRAGMA integrity_check;")
        row = cur.fetchone()
        check = row[0] if row else None
        if check != 'ok':
            src_conn.close()
            flash(f'Целостность загруженной БД нарушена: {check}', 'error')
            return redirect(url_for('database'))

        # Делаем автоснимок текущей БД перед восстановлением
        os.makedirs('backups', exist_ok=True)
        auto_name = f"auto_before_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        auto_path = os.path.join('backups', auto_name)
        try:
            current_conn = sqlite3.connect(DB_PATH)
            auto_conn = sqlite3.connect(auto_path)
            current_conn.backup(auto_conn)
            auto_conn.close()
            current_conn.close()
        except Exception as be:
            # Если не удалось создать автоснимок — прерываем операцию
            src_conn.close()
            flash(f'Не удалось создать автоснимок текущей БД: {be}', 'error')
            return redirect(url_for('database'))

        # Восстанавливаем данные в целевую БД
        dest_conn = sqlite3.connect(DB_PATH)
        src_conn.backup(dest_conn)
        dest_conn.close()
        src_conn.close()

        # Ensure schema has all required columns for current app
        try:
            actions = ensure_schema_compatibility()
            if actions:
                flash('Схема обновлена: ' + ', '.join(actions), 'info')
        except Exception as se:
            flash(f'Предупреждение: не удалось синхронизировать схему: {se}', 'error')

        flash('База данных успешно восстановлена из бэкапа. Создан автоснимок перед восстановлением.', 'success')
    except Exception as e:
        flash(f'Ошибка восстановления БД: {e}', 'error')

    return redirect(url_for('database'))

@app.route('/sync-schema', methods=['POST'])
@login_required
def sync_schema():
    """Manually synchronize DB schema to match current app expectations."""
    try:
        actions = ensure_schema_compatibility()
        if actions:
            flash('Схема синхронизирована: ' + ', '.join(actions), 'success')
        else:
            flash('Схема уже соответствует текущей версии', 'info')
    except Exception as e:
        flash(f'Ошибка синхронизации схемы: {e}', 'error')
    return redirect(url_for('database'))

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