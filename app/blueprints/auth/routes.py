"""Authentication routes."""

import sqlite3
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash

from ...db import get_db
from ...services.validation import sanitize_string
from ...services.currency import CURRENCIES, DEFAULT_CURRENCY

bp = Blueprint('auth', __name__)


@bp.route('/login', methods=['GET', 'POST'])
def login():
    """User login."""
    if request.method == 'POST':
        email = request.form['email'].lower().strip()
        password = request.form['password']
        
        if not email or not password:
            flash('Email и пароль обязательны', 'error')
            return render_template('auth/login.html')
        
        conn = get_db()
        user = conn.execute(
            'SELECT * FROM users WHERE email = ?', (email,)
        ).fetchone()
        conn.close()
        
        if user and check_password_hash(user['password_hash'], password):
            session.clear()
            session['user_id'] = user['id']
            session['name'] = user['name']
            session['theme'] = user.get('theme', 'light')
            session['currency'] = user.get('default_currency', 'RUB')
            return redirect(url_for('dashboard.index'))
        else:
            flash('Неверный email или пароль', 'error')
    
    return render_template('auth/login.html')


@bp.route('/register', methods=['GET', 'POST'])
def register():
    """User registration."""
    if request.method == 'POST':
        name = sanitize_string(request.form.get('name'), 100)
        email = request.form.get('email', '').lower().strip()
        password = request.form.get('password', '')
        
        if not all([name, email, password]):
            flash('Все поля обязательны', 'error')
            return render_template('auth/register.html')
        
        if len(password) < 6:
            flash('Пароль должен содержать минимум 6 символов', 'error')
            return render_template('auth/register.html')
        
        conn = get_db()
        try:
            conn.execute(
                'INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)',
                (name, email, generate_password_hash(password))
            )
            conn.commit()
            flash('Регистрация успешна! Теперь войдите в систему', 'success')
            return redirect(url_for('auth.login'))
        except sqlite3.IntegrityError:
            flash('Пользователь с таким email уже существует', 'error')
        finally:
            conn.close()
    
    return render_template('auth/register.html')


@bp.route('/logout')
def logout():
    """User logout."""
    session.clear()
    flash('Вы вышли из системы', 'info')
    return redirect(url_for('auth.login'))


@bp.route('/set-currency', methods=['POST'])
def set_currency():
    """Set user currency preference."""
    if 'user_id' not in session:
        return {'success': False, 'error': 'Not authenticated'}, 401
    
    payload = request.get_json(silent=True) or {}
    code = (request.form.get("currency") or payload.get("currency") or "").upper()
    
    if code in CURRENCIES:
        session["currency"] = code
        if request.is_json:
            return {"success": True, "currency": code, "symbol": CURRENCIES[code]["symbol"]}
        flash("Валюта обновлена", "success")
    else:
        if request.is_json:
            return {"success": False, "error": "Invalid currency"}, 400
        flash("Неверная валюта", "error")
    
    return redirect(request.referrer or url_for('dashboard.index'))