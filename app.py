import os
import sqlite3
from datetime import datetime, date
from decimal import Decimal, ROUND_HALF_UP
from flask import Flask, render_template, request, redirect, url_for, flash, session
from jinja2 import DictLoader, ChoiceLoader
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret')
DB_PATH = os.environ.get('BUDGET_DB', 'budget.db')

# ----------------------- DB -----------------------
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    return conn

def init_db():
    conn = get_db()
    conn.executescript('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        password_hash TEXT NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        name TEXT NOT NULL,
        limit_type TEXT NOT NULL CHECK(limit_type IN ('fixed','percent')),
        value REAL NOT NULL,
        UNIQUE(user_id, name)
    );

    CREATE TABLE IF NOT EXISTS income (
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        month TEXT NOT NULL,
        amount REAL NOT NULL,
        PRIMARY KEY(user_id, month)
    );

    CREATE TABLE IF NOT EXISTS expenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        date TEXT NOT NULL,
        month TEXT NOT NULL,
        category_id INTEGER NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
        amount REAL NOT NULL,
        note TEXT
    );
    ''')
    conn.commit()
    conn.close()

# ----------------------- LOGIN REQ -----------------------
def login_required(f):
    from functools import wraps
    @wraps(f)
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            flash('Войдите, чтобы продолжить', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return wrapper

# ----------------------- FILTERS -----------------------
def format_amount(value):
    try:
        v = Decimal(str(value)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        return f"{v:,.2f}".replace(',', ' ')
    except:
        return str(value)

app.jinja_env.filters['format_amount'] = format_amount

# ----------------------- ROUTES -----------------------
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        email = request.form['email'].lower().strip()
        name = request.form['name'].strip()
        password = request.form['password']
        confirm = request.form['confirm']

        if password != confirm:
            flash('Пароли не совпадают', 'error')
            return render_template('register.html')

        conn = get_db()
        try:
            conn.execute('INSERT INTO users(email, name, password_hash) VALUES(?,?,?)',
                         (email, name, generate_password_hash(password)))
            conn.commit()
        except sqlite3.IntegrityError:
            flash('Email уже зарегистрирован', 'error')
            return render_template('register.html')
        finally:
            conn.close()

        conn = get_db()
        user = conn.execute('SELECT id FROM users WHERE email=?', (email,)).fetchone()
        conn.close()
        session['user_id'] = user['id']
        session['email'] = email
        session['name'] = name
        return redirect(url_for('dashboard'))
    return render_template('register.html')

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        email = request.form['email'].lower().strip()
        password = request.form['password']
        conn = get_db()
        user = conn.execute('SELECT * FROM users WHERE email=?', (email,)).fetchone()
        conn.close()
        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['email'] = user['email']
            session['name'] = user['name']
            return redirect(url_for('dashboard'))
        flash('Неверный email или пароль', 'error')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    month = request.args.get('month') or datetime.now().strftime('%Y-%m')
    conn = get_db()
    categories = conn.execute('SELECT * FROM categories WHERE user_id=?', (session['user_id'],)).fetchall()
    income = conn.execute('SELECT COALESCE(SUM(amount),0) FROM income WHERE user_id=? AND month=?',
                          (session['user_id'], month)).fetchone()[0]
    expenses = conn.execute('SELECT COALESCE(SUM(amount),0) FROM expenses WHERE user_id=? AND month=?',
                            (session['user_id'], month)).fetchone()[0]
    conn.close()
    return render_template('dashboard.html', categories=categories, income=income, expenses=expenses, current_month=month)

# ----------------------- MAIN -----------------------
if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=True)
