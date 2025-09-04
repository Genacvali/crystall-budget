import os
import sqlite3
from datetime import datetime, date
from flask import Flask, render_template_string, render_template, request, redirect, url_for, flash, jsonify
from jinja2 import DictLoader, ChoiceLoader

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key')

DB_PATH = os.environ.get('BUDGET_DB', 'budget.db')

# Custom Jinja filters
def format_amount(value):
    """Format amount without unnecessary .00"""
    if value == int(value):
        return f"{int(value)}"
    else:
        return f"{value:.2f}".rstrip('0').rstrip('.')

def format_date_with_day(date_str):
    """Format date with day name"""
    try:
        date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
        day_names = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']
        day_name = day_names[date_obj.weekday()]
        return f"{date_str} ({day_name})"
    except:
        return date_str

def format_category_value(value, limit_type):
    """Format category value for display"""
    if limit_type == 'percent':
        # Show as percentage (30 -> 30%)
        return f"{int(value) if value == int(value) else value}%"
    else:
        # Show as amount
        return format_amount(value)

app.jinja_env.filters['format_amount'] = format_amount
app.jinja_env.filters['format_date_with_day'] = format_date_with_day
app.jinja_env.filters['format_category_value'] = format_category_value

# HTML Templates
LAYOUT_TEMPLATE = '''
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}Личный бюджет{% endblock %}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        .btn { min-height: 44px; }
        input, select, textarea { min-height: 44px; }
        .table-responsive { overflow-x: auto; }
        .quick-expense { background-color: #f8f9fa; border-radius: 0.5rem; padding: 1rem; margin-bottom: 1rem; }
        .balance-positive { color: #198754; }
        .balance-negative { color: #dc3545; }
        .balance-warning { color: #fd7e14; }
    </style>
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark bg-dark">
        <div class="container">
            <a class="navbar-brand" href="/">💰 Бюджет</a>
            <div class="navbar-nav ms-auto">
                <a class="nav-link" href="/">Главная</a>
                <a class="nav-link" href="/expenses">Траты</a>
                <a class="nav-link" href="/categories">Категории</a>
                <a class="nav-link" href="/income">Доходы</a>
            </div>
        </div>
    </nav>
    
    <div class="container mt-4">
        {% with messages = get_flashed_messages() %}
            {% if messages %}
                {% for message in messages %}
                    <div class="alert alert-info alert-dismissible fade show" role="alert">
                        {{ message }}
                        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                    </div>
                {% endfor %}
            {% endif %}
        {% endwith %}
        
        {% block content %}{% endblock %}
    </div>
    
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
'''

DASHBOARD_TEMPLATE = '''
{% extends "layout.html" %}
{% block content %}
<div class="row mb-4">
    <div class="col-12">
        <form method="GET" class="d-flex align-items-center gap-3">
            <label for="month" class="form-label mb-0">Месяц:</label>
            <input type="month" id="month" name="month" value="{{ current_month }}" class="form-control" style="width: auto;">
            <button type="submit" class="btn btn-primary">Показать</button>
        </form>
    </div>
</div>

<div class="row mb-4">
    <div class="col-md-4">
        <div class="card text-center">
            <div class="card-body">
                <h5 class="card-title">Доходы</h5>
                <h3 class="text-success">{{ income|format_amount }}</h3>
            </div>
        </div>
    </div>
    <div class="col-md-4">
        <div class="card text-center">
            <div class="card-body">
                <h5 class="card-title">Расходы</h5>
                <h3 class="text-danger">{{ expenses|format_amount }}</h3>
            </div>
        </div>
    </div>
    <div class="col-md-4">
        <div class="card text-center">
            <div class="card-body">
                <h5 class="card-title">Остаток</h5>
                <h3 class="{% if income - expenses > 0 %}text-success{% else %}text-danger{% endif %}">
                    {{ (income - expenses)|format_amount }}
                </h3>
            </div>
        </div>
    </div>
</div>

<div class="quick-expense">
    <h5>Быстрая трата</h5>
    <form method="POST" action="/quick-expense">
        <div class="row g-3">
            <div class="col-12 col-md-3">
                <input type="date" name="date" value="{{ today }}" class="form-control" required>
            </div>
            <div class="col-12 col-md-3">
                <select name="category_id" class="form-select" required>
                    <option value="">Категория</option>
                    {% for cat in categories %}
                    <option value="{{ cat.id }}">{{ cat.name }}</option>
                    {% endfor %}
                </select>
            </div>
            <div class="col-12 col-md-2">
                <input type="number" name="amount" placeholder="Сумма" step="0.01" min="0.01" 
                       inputmode="decimal" class="form-control" required>
            </div>
            <div class="col-12 col-md-2">
                <input type="text" name="note" placeholder="Комментарий" class="form-control">
            </div>
            <div class="col-12 col-md-2">
                <button type="submit" class="btn btn-success w-100">Добавить</button>
            </div>
        </div>
    </form>
</div>

<div class="table-responsive">
    <table class="table table-striped">
        <thead>
            <tr>
                <th>Категория</th>
                <th>Остаток прошлого</th>
                <th>Лимит</th>
                <th>Факт</th>
                <th>Остаток текущий</th>
            </tr>
        </thead>
        <tbody>
            {% for item in budget_data %}
            <tr>
                <td>{{ item.category_name }}</td>
                <td class="{% if item.carryover > 0 %}balance-positive{% elif item.carryover < 0 %}balance-negative{% endif %}">
                    {{ item.carryover|format_amount }}
                </td>
                <td>{{ item.limit|format_amount }}</td>
                <td>{{ item.spent|format_amount }}</td>
                <td class="{% if item.balance > item.limit * 0.2 %}balance-positive{% elif item.balance > 0 %}balance-warning{% else %}balance-negative{% endif %}">
                    {{ item.balance|format_amount }}
                </td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
</div>
{% endblock %}
'''

EXPENSES_TEMPLATE = '''
{% extends "layout.html" %}
{% block title %}Траты - Личный бюджет{% endblock %}
{% block content %}
<div class="d-flex justify-content-between align-items-center mb-4">
    <h2>Траты</h2>
    <button class="btn btn-primary" data-bs-toggle="collapse" data-bs-target="#addExpenseForm">
        Добавить трату
    </button>
</div>

<div class="collapse mb-4" id="addExpenseForm">
    <div class="card card-body">
        <form method="POST" action="/expenses">
            <div class="row g-3">
                <div class="col-md-3">
                    <label for="date" class="form-label">Дата</label>
                    <input type="date" id="date" name="date" value="{{ today }}" class="form-control" required>
                </div>
                <div class="col-md-3">
                    <label for="category_id" class="form-label">Категория</label>
                    <select id="category_id" name="category_id" class="form-select" required>
                        <option value="">Выберите категорию</option>
                        {% for cat in categories %}
                        <option value="{{ cat.id }}">{{ cat.name }}</option>
                        {% endfor %}
                    </select>
                </div>
                <div class="col-md-2">
                    <label for="amount" class="form-label">Сумма</label>
                    <input type="number" id="amount" name="amount" step="0.01" min="0.01" 
                           inputmode="decimal" class="form-control" required>
                </div>
                <div class="col-md-3">
                    <label for="note" class="form-label">Комментарий</label>
                    <input type="text" id="note" name="note" class="form-control">
                </div>
                <div class="col-md-1">
                    <label class="form-label">&nbsp;</label>
                    <button type="submit" class="btn btn-success w-100">Добавить</button>
                </div>
            </div>
        </form>
    </div>
</div>

<div class="table-responsive">
    <table class="table table-striped">
        <thead>
            <tr>
                <th>Дата</th>
                <th>Категория</th>
                <th>Сумма</th>
                <th>Комментарий</th>
                <th>Действия</th>
            </tr>
        </thead>
        <tbody>
            {% for expense in expenses %}
            <tr>
                <td>{{ expense.date|format_date_with_day }}</td>
                <td>{{ expense.category_name }}</td>
                <td>{{ expense.amount|format_amount }}</td>
                <td>{{ expense.note or '' }}</td>
                <td>
                    <form method="POST" action="/expenses/delete/{{ expense.id }}" class="d-inline">
                        <button type="submit" class="btn btn-sm btn-outline-danger" 
                                onclick="return confirm('Удалить трату?')">Удалить</button>
                    </form>
                </td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
</div>
{% endblock %}
'''

CATEGORIES_TEMPLATE = '''
{% extends "layout.html" %}
{% block title %}Категории - Личный бюджет{% endblock %}
{% block content %}
<div class="d-flex justify-content-between align-items-center mb-4">
    <h2>Категории</h2>
    <button class="btn btn-primary" data-bs-toggle="collapse" data-bs-target="#addCategoryForm">
        Добавить категорию
    </button>
</div>

<div class="collapse mb-4" id="addCategoryForm">
    <div class="card card-body">
        <form method="POST" action="/categories/add">
            <div class="row g-3">
                <div class="col-md-4">
                    <label for="name" class="form-label">Название</label>
                    <input type="text" id="name" name="name" class="form-control" required>
                </div>
                <div class="col-md-3">
                    <label for="limit_type" class="form-label">Тип лимита</label>
                    <select id="limit_type" name="limit_type" class="form-select" required>
                        <option value="fixed">Фиксированная сумма</option>
                        <option value="percent">Процент от дохода</option>
                    </select>
                </div>
                <div class="col-md-3">
                    <label for="value" class="form-label">Значение</label>
                    <input type="number" id="value" name="value" step="0.01" min="0.01" 
                           inputmode="decimal" class="form-control" required>
                </div>
                <div class="col-md-2">
                    <label class="form-label">&nbsp;</label>
                    <button type="submit" class="btn btn-success w-100">Добавить</button>
                </div>
            </div>
        </form>
    </div>
</div>

<div class="table-responsive">
    <table class="table table-striped">
        <thead>
            <tr>
                <th>Название</th>
                <th>Тип лимита</th>
                <th>Значение</th>
                <th>Действия</th>
            </tr>
        </thead>
        <tbody>
            {% for cat in categories %}
            <tr>
                <form method="POST" action="/categories/update/{{ cat.id }}" class="d-contents">
                    <td>
                        <input type="text" name="name" value="{{ cat.name }}" class="form-control form-control-sm">
                    </td>
                    <td>
                        <select name="limit_type" class="form-select form-select-sm">
                            <option value="fixed" {% if cat.limit_type == 'fixed' %}selected{% endif %}>Фикс. сумма</option>
                            <option value="percent" {% if cat.limit_type == 'percent' %}selected{% endif %}>% от дохода</option>
                        </select>
                    </td>
                    <td>
                        <input type="number" name="value" value="{{ cat.value }}" step="0.01" min="0.01" 
                               inputmode="decimal" class="form-control form-control-sm">
                    </td>
                    <td>
                        <button type="submit" class="btn btn-sm btn-outline-primary me-2">Сохранить</button>
                </form>
                        <form method="POST" action="/categories/delete/{{ cat.id }}" class="d-inline">
                            <button type="submit" class="btn btn-sm btn-outline-danger" 
                                    onclick="return confirm('Удалить категорию?')">Удалить</button>
                        </form>
                    </td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
</div>
{% endblock %}
'''

INCOME_TEMPLATE = '''
{% extends "layout.html" %}
{% block title %}Доходы - Личный бюджет{% endblock %}
{% block content %}
<div class="row">
    <div class="col-md-6">
        <h2>Доходы</h2>
        <form method="POST" action="/income/add" class="mb-4">
            <div class="row g-3">
                <div class="col-md-6">
                    <label for="month" class="form-label">Месяц</label>
                    <input type="month" id="month" name="month" value="{{ current_month }}" class="form-control" required>
                </div>
                <div class="col-md-4">
                    <label for="amount" class="form-label">Сумма</label>
                    <input type="number" id="amount" name="amount" step="0.01" min="0.01" 
                           inputmode="decimal" class="form-control" required>
                </div>
                <div class="col-md-2">
                    <label class="form-label">&nbsp;</label>
                    <button type="submit" class="btn btn-success w-100">Сохранить</button>
                </div>
            </div>
        </form>
    </div>
</div>

<div class="table-responsive">
    <table class="table table-striped">
        <thead>
            <tr>
                <th>Месяц</th>
                <th>Сумма</th>
            </tr>
        </thead>
        <tbody>
            {% for income in incomes %}
            <tr>
                <td>{{ income.month }}</td>
                <td>{{ income.amount|format_amount }}</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
</div>
{% endblock %}
'''

# Register templates in Jinja loader
app.jinja_loader = ChoiceLoader([
    DictLoader({
        "layout.html": LAYOUT_TEMPLATE,
        "dashboard.html": DASHBOARD_TEMPLATE,
        "expenses.html": EXPENSES_TEMPLATE,
        "categories.html": CATEGORIES_TEMPLATE,
        "income.html": INCOME_TEMPLATE,
    }),
    app.jinja_loader,
])


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    
    # Create tables
    conn.execute('''
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            limit_type TEXT NOT NULL CHECK (limit_type IN ('fixed','percent')),
            value REAL NOT NULL
        )
    ''')
    
    conn.execute('''
        CREATE TABLE IF NOT EXISTS income (
            month TEXT PRIMARY KEY,
            amount REAL NOT NULL
        )
    ''')
    
    conn.execute('''
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            month TEXT NOT NULL,
            category_id INTEGER NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
            amount REAL NOT NULL,
            note TEXT
        )
    ''')
    
    # Insert default categories if none exist
    cursor = conn.execute('SELECT COUNT(*) FROM categories')
    if cursor.fetchone()[0] == 0:
        default_categories = [
            ('Продукты', 'percent', 30),
            ('Транспорт', 'fixed', 5000),
            ('Развлечения', 'percent', 15),
            ('Коммунальные', 'fixed', 8000),
            ('Здоровье', 'fixed', 3000),
            ('Одежда', 'percent', 10)
        ]
        
        for name, limit_type, value in default_categories:
            conn.execute('INSERT INTO categories (name, limit_type, value) VALUES (?, ?, ?)',
                        (name, limit_type, value))
    
    conn.commit()
    conn.close()


def get_current_month():
    return datetime.now().strftime('%Y-%m')


def calculate_limit(month, category, income_amount):
    if category['limit_type'] == 'fixed':
        return float(category['value'])
    else:  # percent
        # Convert percentage to decimal (40 -> 0.40)
        percent_value = float(category['value'])
        if percent_value > 1:
            percent_value = percent_value / 100
        return income_amount * percent_value


def calculate_carryover(month, category_id):
    conn = get_db()
    
    # Get all previous months
    cursor = conn.execute('''
        SELECT DISTINCT month FROM expenses 
        WHERE category_id = ? AND month < ?
        UNION
        SELECT DISTINCT month FROM income WHERE month < ?
        ORDER BY month
    ''', (category_id, month, month))
    
    previous_months = [row['month'] for row in cursor.fetchall()]
    
    total_carryover = 0.0
    
    for prev_month in previous_months:
        # Get income for this month
        cursor = conn.execute('SELECT amount FROM income WHERE month = ?', (prev_month,))
        income_row = cursor.fetchone()
        income_amount = float(income_row['amount']) if income_row else 0.0
        
        # Get category info
        cursor = conn.execute('SELECT * FROM categories WHERE id = ?', (category_id,))
        category = cursor.fetchone()
        
        # Calculate limit for this month
        limit = calculate_limit(prev_month, category, income_amount)
        
        # Calculate spent for this month
        cursor = conn.execute('''
            SELECT COALESCE(SUM(amount), 0) as spent
            FROM expenses 
            WHERE category_id = ? AND month = ?
        ''', (category_id, prev_month))
        spent = float(cursor.fetchone()['spent'])
        
        total_carryover += (limit - spent)
    
    conn.close()
    return total_carryover


def get_dashboard_data(month):
    conn = get_db()
    
    # Get income for month
    cursor = conn.execute('SELECT amount FROM income WHERE month = ?', (month,))
    income_row = cursor.fetchone()
    income = float(income_row['amount']) if income_row else 0.0
    
    # Get total expenses for month
    cursor = conn.execute('''
        SELECT COALESCE(SUM(amount), 0) as total_expenses
        FROM expenses 
        WHERE month = ?
    ''', (month,))
    expenses = float(cursor.fetchone()['total_expenses'])
    
    # Get categories and calculate budget data
    cursor = conn.execute('SELECT * FROM categories ORDER BY name')
    categories = cursor.fetchall()
    
    budget_data = []
    for category in categories:
        # Calculate limit
        limit = calculate_limit(month, category, income)
        
        # Calculate spent this month
        cursor = conn.execute('''
            SELECT COALESCE(SUM(amount), 0) as spent
            FROM expenses 
            WHERE category_id = ? AND month = ?
        ''', (category['id'], month))
        spent = float(cursor.fetchone()['spent'])
        
        # Calculate carryover
        carryover = calculate_carryover(month, category['id'])
        
        # Calculate current balance
        balance = carryover + limit - spent
        
        budget_data.append({
            'category_name': category['name'],
            'carryover': carryover,
            'limit': limit,
            'spent': spent,
            'balance': balance
        })
    
    conn.close()
    return income, expenses, budget_data


@app.route('/')
def dashboard():
    month = request.args.get('month', get_current_month())
    income, expenses, budget_data = get_dashboard_data(month)
    
    conn = get_db()
    cursor = conn.execute('SELECT * FROM categories ORDER BY name')
    categories = cursor.fetchall()
    conn.close()
    
    today = date.today().isoformat()
    
    return render_template("dashboard.html",
                         current_month=month, income=income, expenses=expenses,
                         budget_data=budget_data, categories=categories, today=today)


@app.route('/quick-expense', methods=['POST'])
def quick_expense():
    date_str = request.form['date']
    category_id = request.form['category_id']
    amount = float(request.form['amount'])
    note = request.form.get('note', '')
    
    month = date_str[:7]  # Extract YYYY-MM from YYYY-MM-DD
    
    conn = get_db()
    conn.execute('''
        INSERT INTO expenses (date, month, category_id, amount, note)
        VALUES (?, ?, ?, ?, ?)
    ''', (date_str, month, category_id, amount, note))
    conn.commit()
    conn.close()
    
    flash('Трата добавлена!')
    return redirect(url_for('dashboard'))


@app.route('/expenses')
def expenses():
    conn = get_db()
    
    # Get categories
    cursor = conn.execute('SELECT * FROM categories ORDER BY name')
    categories = cursor.fetchall()
    
    # Get expenses with category names
    cursor = conn.execute('''
        SELECT e.*, c.name as category_name
        FROM expenses e
        JOIN categories c ON e.category_id = c.id
        ORDER BY e.date DESC
    ''')
    expenses_list = cursor.fetchall()
    
    conn.close()
    
    today = date.today().isoformat()
    
    return render_template("expenses.html",
                         expenses=expenses_list, categories=categories, today=today)


@app.route('/expenses', methods=['POST'])
def add_expense():
    date_str = request.form['date']
    category_id = request.form['category_id']
    amount = float(request.form['amount'])
    note = request.form.get('note', '')
    
    month = date_str[:7]  # Extract YYYY-MM from YYYY-MM-DD
    
    conn = get_db()
    conn.execute('''
        INSERT INTO expenses (date, month, category_id, amount, note)
        VALUES (?, ?, ?, ?, ?)
    ''', (date_str, month, category_id, amount, note))
    conn.commit()
    conn.close()
    
    flash('Трата добавлена!')
    return redirect(url_for('expenses'))


@app.route('/expenses/delete/<int:expense_id>', methods=['POST'])
def delete_expense(expense_id):
    conn = get_db()
    conn.execute('DELETE FROM expenses WHERE id = ?', (expense_id,))
    conn.commit()
    conn.close()
    
    flash('Трата удалена!')
    return redirect(url_for('expenses'))


@app.route('/categories')
def categories():
    conn = get_db()
    cursor = conn.execute('SELECT * FROM categories ORDER BY name')
    categories_list = cursor.fetchall()
    conn.close()
    
    return render_template("categories.html",
                         categories=categories_list)


@app.route('/categories/add', methods=['POST'])
def add_category():
    name = request.form['name']
    limit_type = request.form['limit_type']
    value = float(request.form['value'])
    
    conn = get_db()
    try:
        conn.execute('INSERT INTO categories (name, limit_type, value) VALUES (?, ?, ?)',
                    (name, limit_type, value))
        conn.commit()
        flash('Категория добавлена!')
    except sqlite3.IntegrityError:
        flash('Категория с таким названием уже существует!')
    finally:
        conn.close()
    
    return redirect(url_for('categories'))


@app.route('/categories/update/<int:category_id>', methods=['POST'])
def update_category(category_id):
    name = request.form['name']
    limit_type = request.form['limit_type']
    value = float(request.form['value'])
    
    conn = get_db()
    try:
        conn.execute('''
            UPDATE categories 
            SET name = ?, limit_type = ?, value = ?
            WHERE id = ?
        ''', (name, limit_type, value, category_id))
        conn.commit()
        flash('Категория обновлена!')
    except sqlite3.IntegrityError:
        flash('Категория с таким названием уже существует!')
    finally:
        conn.close()
    
    return redirect(url_for('categories'))


@app.route('/categories/delete/<int:category_id>', methods=['POST'])
def delete_category(category_id):
    conn = get_db()
    conn.execute('DELETE FROM categories WHERE id = ?', (category_id,))
    conn.commit()
    conn.close()
    
    flash('Категория удалена!')
    return redirect(url_for('categories'))


@app.route('/income')
def income():
    conn = get_db()
    cursor = conn.execute('SELECT * FROM income ORDER BY month DESC')
    incomes = cursor.fetchall()
    conn.close()
    
    current_month = get_current_month()
    
    return render_template("income.html",
                         incomes=incomes, current_month=current_month)


@app.route('/income/add', methods=['POST'])
def add_income():
    month = request.form['month']
    amount = float(request.form['amount'])
    
    conn = get_db()
    conn.execute('''
        INSERT OR REPLACE INTO income (month, amount)
        VALUES (?, ?)
    ''', (month, amount))
    conn.commit()
    conn.close()
    
    flash('Доход сохранен!')
    return redirect(url_for('income'))


if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=True)