import os
import sqlite3
from datetime import datetime, date
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from flask import Flask, render_template_string, render_template, request, redirect, url_for, flash, jsonify, session
from jinja2 import DictLoader, ChoiceLoader
from markupsafe import escape
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key')

DB_PATH = os.environ.get('BUDGET_DB', 'budget.db')

# Custom Jinja filters
def format_amount(value):
    """Format amount without unnecessary .00"""
    try:
        # Convert to Decimal for precise financial calculations
        if isinstance(value, (int, float, str)):
            decimal_value = Decimal(str(value)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            if decimal_value == decimal_value.to_integral_value():
                return f"{int(decimal_value):,}"
            else:
                formatted = f"{decimal_value:.2f}".rstrip('0').rstrip('.')
                # Add thousand separators
                parts = formatted.split('.')
                parts[0] = f"{int(parts[0]):,}"
                return '.'.join(parts) if len(parts) > 1 else parts[0]
        return "0"
    except (ValueError, TypeError):
        return "0"

def format_date_with_day(date_str):
    """Format date with day name"""
    try:
        date_obj = datetime.strptime(str(date_str), '%Y-%m-%d').date()
        day_names = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']
        day_name = day_names[date_obj.weekday()]
        
        # Format as "15 янв (Пн)" for better mobile readability
        month_names = ['янв', 'фев', 'мар', 'апр', 'май', 'июн',
                      'июл', 'авг', 'сен', 'окт', 'ноя', 'дек']
        month_name = month_names[date_obj.month - 1]
        return f"{date_obj.day} {month_name} ({day_name})"
    except (ValueError, TypeError, AttributeError) as e:
        return str(date_str)

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
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
    <title>{% block title %}CrystalBudget{% endblock %}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.0/font/bootstrap-icons.css" rel="stylesheet">
    <meta name="theme-color" content="#6c5ce7">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="default">
    <style>
        :root {
            --primary-color: #6c5ce7;
            --success-color: #00b894;
            --warning-color: #fdcb6e;
            --danger-color: #e17055;
            --card-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
            --border-radius: 12px;
        }
        
        * { -webkit-tap-highlight-color: transparent; }
        
        body {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        }
        
        .main-content {
            background: #f8f9fa;
            min-height: 100vh;
            border-radius: 20px 20px 0 0;
            margin-top: 1rem;
            padding-top: 1.5rem;
        }
        
        .btn {
            min-height: 44px;
            border-radius: var(--border-radius);
            font-weight: 600;
            transition: all 0.2s ease;
        }
        
        .btn-primary {
            background: var(--primary-color);
            border: none;
            box-shadow: 0 4px 12px rgba(108, 92, 231, 0.3);
        }
        
        .btn-primary:hover {
            background: #5f4fcf;
            transform: translateY(-1px);
            box-shadow: 0 6px 16px rgba(108, 92, 231, 0.4);
        }
        
        .btn-success {
            background: var(--success-color);
            border: none;
        }
        
        input, select, textarea {
            min-height: 44px;
            border-radius: var(--border-radius);
            border: 2px solid #e9ecef;
            transition: all 0.2s ease;
        }
        
        input:focus, select:focus, textarea:focus {
            border-color: var(--primary-color);
            box-shadow: 0 0 0 0.2rem rgba(108, 92, 231, 0.15);
        }
        
        .card {
            border: none;
            border-radius: var(--border-radius);
            box-shadow: var(--card-shadow);
            transition: transform 0.2s ease;
        }
        
        .card:hover {
            transform: translateY(-2px);
        }
        
        .kpi-card {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border-radius: var(--border-radius);
            padding: 1.5rem;
            margin-bottom: 1rem;
        }
        
        .kpi-value {
            font-size: 2rem;
            font-weight: 700;
            margin: 0;
        }
        
        .kpi-label {
            font-size: 0.9rem;
            opacity: 0.8;
            margin: 0;
        }
        
        .quick-expense {
            background: white;
            border-radius: var(--border-radius);
            padding: 1.5rem;
            margin-bottom: 1.5rem;
            box-shadow: var(--card-shadow);
        }
        
        .quick-expense h5 {
            color: var(--primary-color);
            font-weight: 600;
            margin-bottom: 1rem;
        }
        
        .table-responsive {
            overflow-x: auto;
            border-radius: var(--border-radius);
            box-shadow: var(--card-shadow);
            background: white;
        }
        
        .table {
            margin-bottom: 0;
        }
        
        .table th {
            background: #f8f9fa;
            border: none;
            font-weight: 600;
            padding: 1rem 0.75rem;
        }
        
        .table td {
            border: none;
            border-bottom: 1px solid #f1f3f4;
            padding: 1rem 0.75rem;
            vertical-align: middle;
        }
        
        .balance-positive { color: var(--success-color); font-weight: 600; }
        .balance-negative { color: var(--danger-color); font-weight: 600; }
        .balance-warning { color: var(--warning-color); font-weight: 600; }
        
        .navbar {
            background: transparent !important;
            padding: 1rem 0;
        }
        
        .navbar-brand {
            color: white !important;
            font-weight: 700;
            font-size: 1.5rem;
        }
        
        .nav-link {
            color: rgba(255, 255, 255, 0.9) !important;
            font-weight: 500;
        }
        
        .alert {
            border: none;
            border-radius: var(--border-radius);
            box-shadow: var(--card-shadow);
        }
        
        .month-selector {
            background: white;
            border-radius: var(--border-radius);
            padding: 1rem;
            margin-bottom: 1.5rem;
            box-shadow: var(--card-shadow);
        }
        
        .expense-item {
            background: white;
            border-radius: var(--border-radius);
            padding: 1rem;
            margin-bottom: 0.5rem;
            box-shadow: var(--card-shadow);
            border-left: 4px solid var(--primary-color);
        }
        
        .category-badge {
            background: var(--primary-color);
            color: white;
            padding: 0.25rem 0.75rem;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: 500;
        }
        
        @media (max-width: 768px) {
            .main-content { margin-top: 0; border-radius: 0; }
            .container { padding-left: 1rem; padding-right: 1rem; }
            .kpi-value { font-size: 1.5rem; }
            .quick-expense { padding: 1rem; }
        }
    </style>
</head>
<body>
    <nav class="navbar navbar-expand-lg">
        <div class="container">
            <a class="navbar-brand" href="/"><i class="bi bi-gem"></i> CrystalBudget</a>
            {% if session.user_id %}
            <div class="navbar-nav ms-auto">
                <a class="nav-link" href="{{ url_for('dashboard') }}"><i class="bi bi-house"></i> <span class="d-none d-md-inline">Главная</span></a>
                <a class="nav-link" href="{{ url_for('expenses') }}"><i class="bi bi-receipt"></i> <span class="d-none d-md-inline">Траты</span></a>
                <a class="nav-link" href="{{ url_for('categories') }}"><i class="bi bi-tags"></i> <span class="d-none d-md-inline">Категории</span></a>
                <a class="nav-link" href="{{ url_for('income') }}"><i class="bi bi-graph-up"></i> <span class="d-none d-md-inline">Доходы</span></a>
                <div class="nav-item dropdown">
                    <a class="nav-link dropdown-toggle" href="#" role="button" data-bs-toggle="dropdown">
                        <i class="bi bi-person-circle"></i> <span class="d-none d-md-inline">{{ session.user_name }}</span>
                    </a>
                    <ul class="dropdown-menu dropdown-menu-end">
                        <li><a class="dropdown-item" href="{{ url_for('logout') }}"><i class="bi bi-box-arrow-right"></i> Выйти</a></li>
                    </ul>
                </div>
            </div>
            {% endif %}
        </div>
    </nav>
    
    <div class="main-content">
    <div class="container">
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    {% set alert_class = 'alert-success' if category == 'success' else ('alert-danger' if category == 'error' else 'alert-info') %}
                    {% set icon = 'check-circle-fill' if category == 'success' else ('exclamation-triangle-fill' if category == 'error' else 'info-circle-fill') %}
                    <div class="alert {{ alert_class }} alert-dismissible fade show d-flex align-items-center" role="alert">
                        <i class="bi bi-{{ icon }} me-2"></i>
                        {{ message }}
                        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                    </div>
                {% endfor %}
            {% endif %}
        {% endwith %}
        
        {% block content %}{% endblock %}
    </div>
    </div>
    
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
'''

DASHBOARD_TEMPLATE = '''
{% extends "layout.html" %}
{% block content %}
<div class="month-selector">
    <form method="GET" class="row align-items-center">
        <div class="col-auto">
            <label for="month" class="form-label mb-0 fw-bold">Месяц:</label>
        </div>
        <div class="col">
            <input type="month" id="month" name="month" value="{{ current_month }}" class="form-control">
        </div>
        <div class="col-auto">
            <button type="submit" class="btn btn-primary">
                <i class="bi bi-search"></i> Показать
            </button>
        </div>
    </form>
</div>

<div class="row mb-4">
    <div class="col-12">
        <div class="kpi-card">
            <div class="row text-center">
                <div class="col-4">
                    <p class="kpi-label"><i class="bi bi-arrow-down-circle"></i> Доходы</p>
                    <p class="kpi-value">{{ income|format_amount }}</p>
                </div>
                <div class="col-4">
                    <p class="kpi-label"><i class="bi bi-arrow-up-circle"></i> Расходы</p>
                    <p class="kpi-value">{{ expenses|format_amount }}</p>
                </div>
                <div class="col-4">
                    <p class="kpi-label"><i class="bi bi-wallet"></i> Остаток</p>
                    <p class="kpi-value">{{ (income - expenses)|format_amount }}</p>
                </div>
            </div>
        </div>
    </div>
</div>

<div class="quick-expense">
    <h5><i class="bi bi-plus-circle"></i> Быстрая трата</h5>
    <form method="POST" action="/quick-expense">
        <div class="row g-3">
            <div class="col-12 col-md-3">
                <label class="form-label text-muted"><i class="bi bi-calendar"></i> Дата</label>
                <input type="date" name="date" value="{{ today }}" class="form-control" required>
            </div>
            <div class="col-12 col-md-3">
                <label class="form-label text-muted"><i class="bi bi-tag"></i> Категория</label>
                <select name="category_id" class="form-select" required>
                    <option value="">Выберите категорию</option>
                    {% for cat in categories %}
                    <option value="{{ cat.id }}">{{ cat.name }}</option>
                    {% endfor %}
                </select>
            </div>
            <div class="col-12 col-md-2">
                <label class="form-label text-muted"><i class="bi bi-currency-exchange"></i> Сумма</label>
                <input type="number" name="amount" placeholder="0" step="0.01" min="0.01" 
                       inputmode="decimal" class="form-control" required>
            </div>
            <div class="col-12 col-md-2">
                <label class="form-label text-muted"><i class="bi bi-chat"></i> Комментарий</label>
                <input type="text" name="note" placeholder="Описание" class="form-control">
            </div>
            <div class="col-12 col-md-2">
                <label class="form-label" style="opacity: 0;">&nbsp;</label>
                <button type="submit" class="btn btn-success w-100">
                    <i class="bi bi-plus-lg"></i> Добавить
                </button>
            </div>
        </div>
    </form>
</div>

<div class="d-block d-md-none">
    <!-- Mobile card view -->
    {% for item in budget_data %}
    <div class="card mb-3">
        <div class="card-body">
            <div class="d-flex justify-content-between align-items-center mb-2">
                <h6 class="card-title mb-0 fw-bold">{{ item.category_name }}</h6>
                <span class="category-badge">{{ item.category_name[:3] }}</span>
            </div>
            <div class="row text-center">
                <div class="col-3">
                    <small class="text-muted d-block">Прошлое</small>
                    <span class="fw-bold {% if item.carryover > 0 %}balance-positive{% elif item.carryover < 0 %}balance-negative{% endif %}">
                        {{ item.carryover|format_amount }}
                    </span>
                </div>
                <div class="col-3">
                    <small class="text-muted d-block">Лимит</small>
                    <span class="fw-bold">{{ item.limit|format_amount }}</span>
                </div>
                <div class="col-3">
                    <small class="text-muted d-block">Траты</small>
                    <span class="fw-bold">{{ item.spent|format_amount }}</span>
                </div>
                <div class="col-3">
                    <small class="text-muted d-block">Остаток</small>
                    <span class="fw-bold {% if item.balance > item.limit * 0.2 %}balance-positive{% elif item.balance > 0 %}balance-warning{% else %}balance-negative{% endif %}">
                        {{ item.balance|format_amount }}
                    </span>
                </div>
            </div>
            <!-- Progress bar -->
            <div class="mt-3">
                {% set progress_percent = ((item.spent / item.limit * 100) if item.limit > 0 else 0) | round(1) %}
                <div class="progress" style="height: 6px;">
                    <div class="progress-bar {% if progress_percent < 50 %}bg-success{% elif progress_percent < 80 %}bg-warning{% else %}bg-danger{% endif %}" 
                         style="width: {{ [progress_percent, 100] | min }}%"></div>
                </div>
                <small class="text-muted">{{ progress_percent }}% использовано</small>
            </div>
        </div>
    </div>
    {% endfor %}
</div>

<div class="table-responsive d-none d-md-block">
    <!-- Desktop table view -->
    <table class="table">
        <thead>
            <tr>
                <th><i class="bi bi-tag"></i> Категория</th>
                <th class="text-center"><i class="bi bi-arrow-left"></i> Прошлое</th>
                <th class="text-center"><i class="bi bi-bullseye"></i> Лимит</th>
                <th class="text-center"><i class="bi bi-receipt"></i> Траты</th>
                <th class="text-center"><i class="bi bi-wallet"></i> Остаток</th>
                <th class="text-center">Прогресс</th>
            </tr>
        </thead>
        <tbody>
            {% for item in budget_data %}
            <tr>
                <td class="fw-bold">{{ item.category_name }}</td>
                <td class="text-center {% if item.carryover > 0 %}balance-positive{% elif item.carryover < 0 %}balance-negative{% endif %}">
                    {{ item.carryover|format_amount }}
                </td>
                <td class="text-center">{{ item.limit|format_amount }}</td>
                <td class="text-center">{{ item.spent|format_amount }}</td>
                <td class="text-center {% if item.balance > item.limit * 0.2 %}balance-positive{% elif item.balance > 0 %}balance-warning{% else %}balance-negative{% endif %}">
                    {{ item.balance|format_amount }}
                </td>
                <td class="text-center">
                    {% set progress_percent = ((item.spent / item.limit * 100) if item.limit > 0 else 0) | round(1) %}
                    <div class="progress" style="height: 6px; width: 60px;">
                        <div class="progress-bar {% if progress_percent < 50 %}bg-success{% elif progress_percent < 80 %}bg-warning{% else %}bg-danger{% endif %}" 
                             style="width: {{ [progress_percent, 100] | min }}%"></div>
                    </div>
                    <small>{{ progress_percent }}%</small>
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

LOGIN_TEMPLATE = '''
{% extends "layout.html" %}
{% block title %}Вход - CrystalBudget{% endblock %}
{% block content %}
<div class="row justify-content-center">
    <div class="col-md-6 col-lg-4">
        <div class="card" style="margin-top: 2rem;">
            <div class="card-body p-4">
                <div class="text-center mb-4">
                    <i class="bi bi-gem" style="font-size: 3rem; color: var(--primary-color);"></i>
                    <h2 class="mt-3">CrystalBudget</h2>
                    <p class="text-muted">Войдите в свой аккаунт</p>
                </div>
                
                <form method="POST">
                    <div class="mb-3">
                        <label for="email" class="form-label"><i class="bi bi-envelope"></i> Email</label>
                        <input type="email" class="form-control" id="email" name="email" required 
                               value="{{ request.form.get('email', '') }}">
                    </div>
                    
                    <div class="mb-3">
                        <label for="password" class="form-label"><i class="bi bi-lock"></i> Пароль</label>
                        <input type="password" class="form-control" id="password" name="password" required>
                    </div>
                    
                    <button type="submit" class="btn btn-primary w-100 mb-3">
                        <i class="bi bi-box-arrow-in-right"></i> Войти
                    </button>
                </form>
                
                <div class="text-center">
                    <p class="mb-0">Нет аккаунта? <a href="{{ url_for('register') }}" class="text-decoration-none">Зарегистрироваться</a></p>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}
'''

REGISTER_TEMPLATE = '''
{% extends "layout.html" %}
{% block title %}Регистрация - CrystalBudget{% endblock %}
{% block content %}
<div class="row justify-content-center">
    <div class="col-md-6 col-lg-4">
        <div class="card" style="margin-top: 2rem;">
            <div class="card-body p-4">
                <div class="text-center mb-4">
                    <i class="bi bi-gem" style="font-size: 3rem; color: var(--primary-color);"></i>
                    <h2 class="mt-3">CrystalBudget</h2>
                    <p class="text-muted">Создайте новый аккаунт</p>
                </div>
                
                <form method="POST">
                    <div class="mb-3">
                        <label for="name" class="form-label"><i class="bi bi-person"></i> Имя</label>
                        <input type="text" class="form-control" id="name" name="name" required 
                               value="{{ request.form.get('name', '') }}" minlength="2">
                    </div>
                    
                    <div class="mb-3">
                        <label for="email" class="form-label"><i class="bi bi-envelope"></i> Email</label>
                        <input type="email" class="form-control" id="email" name="email" required 
                               value="{{ request.form.get('email', '') }}">
                    </div>
                    
                    <div class="mb-3">
                        <label for="password" class="form-label"><i class="bi bi-lock"></i> Пароль</label>
                        <input type="password" class="form-control" id="password" name="password" required minlength="6">
                        <div class="form-text">Минимум 6 символов</div>
                    </div>
                    
                    <div class="mb-3">
                        <label for="confirm_password" class="form-label"><i class="bi bi-lock-fill"></i> Подтвердите пароль</label>
                        <input type="password" class="form-control" id="confirm_password" name="confirm_password" required>
                    </div>
                    
                    <button type="submit" class="btn btn-primary w-100 mb-3">
                        <i class="bi bi-person-plus"></i> Зарегистрироваться
                    </button>
                </form>
                
                <div class="text-center">
                    <p class="mb-0">Уже есть аккаунт? <a href="{{ url_for('login') }}" class="text-decoration-none">Войти</a></p>
                </div>
            </div>
        </div>
    </div>
</div>

<script>
// Check password confirmation
document.getElementById('confirm_password').addEventListener('input', function() {
    const password = document.getElementById('password').value;
    const confirmPassword = this.value;
    
    if (password !== confirmPassword) {
        this.setCustomValidity('Пароли не совпадают');
    } else {
        this.setCustomValidity('');
    }
});
</script>
{% endblock %}
'''

# Register templates in Jinja loader
app.jinja_loader = ChoiceLoader([
    DictLoader({
        "layout.html": LAYOUT_TEMPLATE,
        "login.html": LOGIN_TEMPLATE,
        "register.html": REGISTER_TEMPLATE,
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
    # Enable foreign key constraints for data integrity
    conn.execute('PRAGMA foreign_keys = ON')
    return conn


def check_and_migrate_db():
    """Check database schema and migrate if needed"""
    conn = get_db()
    
    try:
        # Check if users table exists
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
        users_exists = cursor.fetchone() is not None
        
        if not users_exists:
            print("[MIGRATE] Creating new database with user authentication...")
            init_fresh_db(conn)
        else:
            # Check if old tables need migration
            cursor = conn.execute("PRAGMA table_info(categories)")
            columns = [col[1] for col in cursor.fetchall()]
            
            if 'user_id' not in columns:
                print("[MIGRATE] Migrating existing database to multi-user schema...")
                migrate_existing_db(conn)
            else:
                print("[INFO] Database schema is up to date")
                
    except Exception as e:
        print(f"[ERROR] Database migration failed: {e}")
        # If migration fails, backup and recreate
        import shutil
        import time
        backup_name = f"budget_backup_{int(time.time())}.db"
        try:
            shutil.copy(DB_PATH, backup_name)
            print(f"[BACKUP] Old database backed up to {backup_name}")
        except:
            pass
        
        conn.close()
        os.remove(DB_PATH)
        conn = get_db()
        init_fresh_db(conn)
        print("[MIGRATE] Created fresh database (old data backed up)")
    
    conn.commit()
    conn.close()

def init_fresh_db(conn):
    """Initialize fresh database with user authentication"""
    
    # Create users table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            name TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create categories table with user_id
    conn.execute('''
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            name TEXT NOT NULL,
            limit_type TEXT NOT NULL CHECK (limit_type IN ('fixed','percent')),
            value REAL NOT NULL,
            UNIQUE(user_id, name)
        )
    ''')
    
    # Create income table with user_id
    conn.execute('''
        CREATE TABLE IF NOT EXISTS income (
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            month TEXT NOT NULL,
            amount REAL NOT NULL,
            PRIMARY KEY (user_id, month)
        )
    ''')
    
    # Create expenses table with user_id
    conn.execute('''
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            date TEXT NOT NULL,
            month TEXT NOT NULL,
            category_id INTEGER NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
            amount REAL NOT NULL,
            note TEXT
        )
    ''')

def migrate_existing_db(conn):
    """Migrate existing single-user database to multi-user"""
    
    # Create users table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            name TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create a default user for existing data
    default_password = generate_password_hash('admin123')
    
    cursor = conn.execute('''
        INSERT INTO users (email, password_hash, name) 
        VALUES ('admin@crystalbudget.local', ?, 'Admin User')
    ''', (default_password,))
    
    default_user_id = cursor.lastrowid
    print(f"[MIGRATE] Created default user: admin@crystalbudget.local / admin123 (ID: {default_user_id})")
    
    # Rename old tables
    conn.execute('ALTER TABLE categories RENAME TO categories_old')
    conn.execute('ALTER TABLE income RENAME TO income_old')
    conn.execute('ALTER TABLE expenses RENAME TO expenses_old')
    
    # Create new tables with user_id
    conn.execute('''
        CREATE TABLE categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            name TEXT NOT NULL,
            limit_type TEXT NOT NULL CHECK (limit_type IN ('fixed','percent')),
            value REAL NOT NULL,
            UNIQUE(user_id, name)
        )
    ''')
    
    conn.execute('''
        CREATE TABLE income (
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            month TEXT NOT NULL,
            amount REAL NOT NULL,
            PRIMARY KEY (user_id, month)
        )
    ''')
    
    conn.execute('''
        CREATE TABLE expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            date TEXT NOT NULL,
            month TEXT NOT NULL,
            category_id INTEGER NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
            amount REAL NOT NULL,
            note TEXT
        )
    ''')
    
    # Migrate data
    # Migrate categories
    conn.execute('''
        INSERT INTO categories (id, user_id, name, limit_type, value)
        SELECT id, ?, name, limit_type, value FROM categories_old
    ''', (default_user_id,))
    
    # Migrate income
    conn.execute('''
        INSERT INTO income (user_id, month, amount)
        SELECT ?, month, amount FROM income_old
    ''', (default_user_id,))
    
    # Migrate expenses
    conn.execute('''
        INSERT INTO expenses (id, user_id, date, month, category_id, amount, note)
        SELECT id, ?, date, month, category_id, amount, note FROM expenses_old
    ''', (default_user_id,))
    
    # Drop old tables
    conn.execute('DROP TABLE categories_old')
    conn.execute('DROP TABLE income_old')
    conn.execute('DROP TABLE expenses_old')
    
    print("[MIGRATE] Successfully migrated existing data to multi-user schema")

def init_db():
    """Legacy function - now just calls check_and_migrate_db"""
    check_and_migrate_db()

def create_default_categories(user_id):
    """Create default categories for new user"""
    default_categories = [
        ('Продукты', 'percent', 30),
        ('Транспорт', 'fixed', 5000),
        ('Развлечения', 'percent', 15),
        ('Коммунальные', 'fixed', 8000),
        ('Здоровье', 'fixed', 3000),
        ('Одежда', 'percent', 10)
    ]
    
    def add_categories_op(conn, user_id, categories):
        for name, limit_type, value in categories:
            conn.execute('INSERT INTO categories (user_id, name, limit_type, value) VALUES (?, ?, ?, ?)',
                        (user_id, name, limit_type, value))
        return len(categories)
    
    return safe_db_operation(add_categories_op, user_id, default_categories)


def get_current_month():
    return datetime.now().strftime('%Y-%m')

def validate_amount(amount_str):
    """Validate and convert amount to Decimal"""
    try:
        amount = Decimal(str(amount_str).replace(',', ''))
        if amount <= 0:
            raise ValueError("Amount must be positive")
        return amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    except (ValueError, TypeError, InvalidOperation):
        raise ValueError("Invalid amount format")

def validate_date(date_str):
    """Validate date format and check if not in future"""
    try:
        date_obj = datetime.strptime(str(date_str), '%Y-%m-%d').date()
        if date_obj > date.today():
            raise ValueError("Date cannot be in the future")
        return date_obj
    except (ValueError, TypeError) as e:
        raise ValueError(f"Invalid date: {e}")

def safe_db_operation(operation, *args, **kwargs):
    """Safely execute database operation with error handling"""
    conn = None
    try:
        conn = get_db()
        result = operation(conn, *args, **kwargs)
        conn.commit()
        return result
    except sqlite3.IntegrityError as e:
        if conn:
            conn.rollback()
        if "UNIQUE constraint" in str(e):
            raise ValueError("This item already exists")
        elif "FOREIGN KEY constraint" in str(e):
            raise ValueError("Referenced item does not exist")
        else:
            raise ValueError(f"Database constraint error: {e}")
    except sqlite3.Error as e:
        if conn:
            conn.rollback()
        raise ValueError(f"Database error: {e}")
    except Exception as e:
        if conn:
            conn.rollback()
        raise ValueError(f"Unexpected error: {e}")
    finally:
        if conn:
            conn.close()

def login_required(f):
    """Decorator to require login for routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Необходимо войти в систему', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


def calculate_carryover(month, category_id, user_id):
    conn = get_db()
    
    # Get all previous months
    cursor = conn.execute('''
        SELECT DISTINCT month FROM expenses 
        WHERE category_id = ? AND month < ? AND user_id = ?
        UNION
        SELECT DISTINCT month FROM income WHERE month < ? AND user_id = ?
        ORDER BY month
    ''', (category_id, month, user_id, month, user_id))
    
    previous_months = [row['month'] for row in cursor.fetchall()]
    
    total_carryover = 0.0
    
    for prev_month in previous_months:
        # Get income for this month
        cursor = conn.execute('SELECT amount FROM income WHERE month = ? AND user_id = ?', (prev_month, user_id))
        income_row = cursor.fetchone()
        income_amount = float(income_row['amount']) if income_row else 0.0
        
        # Get category info
        cursor = conn.execute('SELECT * FROM categories WHERE id = ? AND user_id = ?', (category_id, user_id))
        category = cursor.fetchone()
        
        # Calculate limit for this month using proper logic
        if category['limit_type'] == 'fixed':
            limit = float(category['value'])
        else:  # percent - need to calculate from remaining income
            # Get all fixed categories total for this month
            cursor = conn.execute('SELECT * FROM categories WHERE limit_type = "fixed" AND user_id = ?', (user_id,))
            fixed_categories = cursor.fetchall()
            total_fixed = sum(float(cat['value']) for cat in fixed_categories)
            
            remaining_income = max(0, income_amount - total_fixed)
            percent_value = float(category['value'])
            if percent_value > 1:
                percent_value = percent_value / 100
            limit = remaining_income * percent_value
        
        # Calculate spent for this month
        cursor = conn.execute('''
            SELECT COALESCE(SUM(amount), 0) as spent
            FROM expenses 
            WHERE category_id = ? AND month = ? AND user_id = ?
        ''', (category_id, prev_month, user_id))
        spent = float(cursor.fetchone()['spent'])
        
        total_carryover += (limit - spent)
    
    conn.close()
    return total_carryover


def get_dashboard_data(month, user_id):
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
    
    # First pass: calculate total fixed limits
    total_fixed = 0.0
    for category in categories:
        if category['limit_type'] == 'fixed':
            total_fixed += float(category['value'])
    
    # Remaining income for percentage categories
    remaining_income = max(0, income - total_fixed)
    
    budget_data = []
    for category in categories:
        # Calculate limit using remaining income for percentages
        if category['limit_type'] == 'fixed':
            limit = float(category['value'])
        else:  # percent
            percent_value = float(category['value'])
            if percent_value > 1:
                percent_value = percent_value / 100
            limit = remaining_income * percent_value
        
        # Calculate spent this month
        cursor = conn.execute('''
            SELECT COALESCE(SUM(amount), 0) as spent
            FROM expenses 
            WHERE category_id = ? AND month = ?
        ''', (category['id'], month))
        spent = float(cursor.fetchone()['spent'])
        
        # Calculate carryover
        carryover = calculate_carryover(month, category['id'], user_id)
        
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

# Authentication Routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        try:
            email = request.form.get('email', '').strip().lower()
            password = request.form.get('password', '')
            
            if not email or not password:
                flash('Пожалуйста, заполните все поля', 'error')
                return render_template('login.html')
            
            # Find user in database
            def find_user_op(conn, email):
                cursor = conn.execute('SELECT id, name, password_hash FROM users WHERE email = ?', (email,))
                return cursor.fetchone()
            
            user = safe_db_operation(find_user_op, email)
            
            if user and check_password_hash(user['password_hash'], password):
                # Login successful
                session['user_id'] = user['id']
                session['user_name'] = user['name']
                session['user_email'] = email
                
                flash(f'Добро пожаловать, {user["name"]}!', 'success')
                return redirect(url_for('dashboard'))
            else:
                flash('Неверные email или пароль', 'error')
                
        except ValueError as e:
            flash(f'Ошибка: {str(e)}', 'error')
        except Exception as e:
            flash('Произошла ошибка при входе', 'error')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        try:
            name = escape(request.form.get('name', '').strip())
            email = request.form.get('email', '').strip().lower()
            password = request.form.get('password', '')
            confirm_password = request.form.get('confirm_password', '')
            
            # Validation
            if not all([name, email, password, confirm_password]):
                flash('Пожалуйста, заполните все поля', 'error')
                return render_template('register.html')
            
            if len(name) < 2:
                flash('Имя должно содержать минимум 2 символа', 'error')
                return render_template('register.html')
                
            if len(password) < 6:
                flash('Пароль должен содержать минимум 6 символов', 'error')
                return render_template('register.html')
                
            if password != confirm_password:
                flash('Пароли не совпадают', 'error')
                return render_template('register.html')
            
            # Email format validation (basic)
            if '@' not in email or '.' not in email.split('@')[1]:
                flash('Пожалуйста, введите корректный email', 'error')
                return render_template('register.html')
            
            # Create user
            password_hash = generate_password_hash(password)
            
            def create_user_op(conn, name, email, password_hash):
                cursor = conn.execute(
                    'INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)',
                    (name, email, password_hash)
                )
                return cursor.lastrowid
            
            user_id = safe_db_operation(create_user_op, name, email, password_hash)
            
            # Create default categories for new user
            create_default_categories(user_id)
            
            # Auto-login after registration
            session['user_id'] = user_id
            session['user_name'] = name
            session['user_email'] = email
            
            flash(f'Добро пожаловать в CrystalBudget, {name}! Для вас созданы категории по умолчанию.', 'success')
            return redirect(url_for('dashboard'))
            
        except ValueError as e:
            if "already exists" in str(e):
                flash('Пользователь с таким email уже существует', 'error')
            else:
                flash(f'Ошибка: {str(e)}', 'error')
        except Exception as e:
            flash('Произошла ошибка при регистрации', 'error')
    
    return render_template('register.html')

@app.route('/logout')
def logout():
    name = session.get('user_name', 'Пользователь')
    session.clear()
    flash(f'До свидания, {name}!', 'success')
    return redirect(url_for('login'))

# Main Routes
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    month = request.args.get('month', get_current_month())
    user_id = session['user_id']
    income, expenses, budget_data = get_dashboard_data(month, user_id)
    
    conn = get_db()
    cursor = conn.execute('SELECT * FROM categories WHERE user_id = ? ORDER BY name', (user_id,))
    categories = cursor.fetchall()
    conn.close()
    
    today = date.today().isoformat()
    
    return render_template("dashboard.html",
                         current_month=month, income=income, expenses=expenses,
                         budget_data=budget_data, categories=categories, today=today)


@app.route('/quick-expense', methods=['POST'])
def quick_expense():
    try:
        # Validate inputs
        date_str = request.form.get('date', '').strip()
        category_id = request.form.get('category_id', '').strip()
        amount_str = request.form.get('amount', '').strip()
        note = escape(request.form.get('note', '').strip())
        
        if not date_str or not category_id or not amount_str:
            flash('Ошибка: все обязательные поля должны быть заполнены', 'error')
            return redirect(url_for('dashboard'))
        
        # Validate and convert data
        validated_date = validate_date(date_str)
        amount = validate_amount(amount_str)
        month = validated_date.strftime('%Y-%m')
        
        # Database operation
        user_id = session['user_id']
        def add_expense_op(conn, user_id, date_str, month, category_id, amount, note):
            cursor = conn.execute('''
                INSERT INTO expenses (user_id, date, month, category_id, amount, note)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (user_id, date_str, month, int(category_id), float(amount), note))
            return cursor.rowcount
        
        result = safe_db_operation(add_expense_op, user_id, date_str, month, category_id, amount, note)
        
        if result > 0:
            flash(f'✓ Трата {amount} руб. добавлена!', 'success')
        else:
            flash('Ошибка при добавлении траты', 'error')
            
    except ValueError as e:
        flash(f'Ошибка: {str(e)}', 'error')
    except Exception as e:
        flash(f'Неожиданная ошибка: {str(e)}', 'error')
    
    return redirect(url_for('dashboard'))


@app.route('/expenses')
@login_required
def expenses():
    user_id = session['user_id']
    conn = get_db()
    
    # Get categories
    cursor = conn.execute('SELECT * FROM categories WHERE user_id = ? ORDER BY name', (user_id,))
    categories = cursor.fetchall()
    
    # Get expenses with category names
    cursor = conn.execute('''
        SELECT e.*, c.name as category_name
        FROM expenses e
        JOIN categories c ON e.category_id = c.id
        WHERE e.user_id = ?
        ORDER BY e.date DESC
    ''', (user_id,))
    expenses_list = cursor.fetchall()
    
    conn.close()
    
    today = date.today().isoformat()
    
    return render_template("expenses.html",
                         expenses=expenses_list, categories=categories, today=today)


@app.route('/expenses', methods=['POST'])
@login_required
def add_expense():
    try:
        user_id = session['user_id']
        date_str = request.form.get('date', '').strip()
        category_id = request.form.get('category_id', '').strip()
        amount_str = request.form.get('amount', '').strip()
        note = escape(request.form.get('note', '').strip())
        
        if not date_str or not category_id or not amount_str:
            flash('Ошибка: все обязательные поля должны быть заполнены', 'error')
            return redirect(url_for('expenses'))
        
        validated_date = validate_date(date_str)
        amount = validate_amount(amount_str)
        month = validated_date.strftime('%Y-%m')
        
        def add_expense_op(conn, user_id, date_str, month, category_id, amount, note):
            cursor = conn.execute('''
                INSERT INTO expenses (user_id, date, month, category_id, amount, note)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (user_id, date_str, month, int(category_id), float(amount), note))
            return cursor.rowcount
        
        result = safe_db_operation(add_expense_op, user_id, date_str, month, category_id, amount, note)
        
        if result > 0:
            flash(f'✓ Трата {amount} руб. добавлена!', 'success')
        else:
            flash('Ошибка при добавлении траты', 'error')
            
    except ValueError as e:
        flash(f'Ошибка: {str(e)}', 'error')
    except Exception as e:
        flash(f'Неожиданная ошибка: {str(e)}', 'error')
    
    return redirect(url_for('expenses'))


@app.route('/expenses/delete/<int:expense_id>', methods=['POST'])
@login_required
def delete_expense(expense_id):
    try:
        user_id = session['user_id']
        
        def delete_expense_op(conn, user_id, expense_id):
            cursor = conn.execute('DELETE FROM expenses WHERE id = ? AND user_id = ?', (expense_id, user_id))
            return cursor.rowcount
        
        result = safe_db_operation(delete_expense_op, user_id, expense_id)
        
        if result > 0:
            flash('✓ Трата удалена!', 'success')
        else:
            flash('Трата не найдена', 'error')
            
    except Exception as e:
        flash(f'Ошибка при удалении: {str(e)}', 'error')
    
    return redirect(url_for('expenses'))


@app.route('/categories')
@login_required
def categories():
    user_id = session['user_id']
    conn = get_db()
    cursor = conn.execute('SELECT * FROM categories WHERE user_id = ? ORDER BY name', (user_id,))
    categories_list = cursor.fetchall()
    conn.close()
    
    return render_template("categories.html",
                         categories=categories_list)


@app.route('/categories/add', methods=['POST'])
@login_required
def add_category():
    try:
        user_id = session['user_id']
        name = escape(request.form.get('name', '').strip())
        limit_type = request.form.get('limit_type', '').strip()
        value_str = request.form.get('value', '').strip()
        
        if not name or not limit_type or not value_str:
            flash('Пожалуйста, заполните все поля', 'error')
            return redirect(url_for('categories'))
            
        if limit_type not in ['fixed', 'percent']:
            flash('Некорректный тип лимита', 'error')
            return redirect(url_for('categories'))
            
        value = validate_amount(value_str)
        
        def add_category_op(conn, user_id, name, limit_type, value):
            cursor = conn.execute(
                'INSERT INTO categories (user_id, name, limit_type, value) VALUES (?, ?, ?, ?)',
                (user_id, name, limit_type, float(value))
            )
            return cursor.rowcount
            
        result = safe_db_operation(add_category_op, user_id, name, limit_type, value)
        
        if result > 0:
            flash(f'✓ Категория "{name}" добавлена!', 'success')
        else:
            flash('Ошибка при добавлении категории', 'error')
            
    except ValueError as e:
        if "already exists" in str(e):
            flash('Категория с таким названием уже существует!', 'error')
        else:
            flash(f'Ошибка: {str(e)}', 'error')
    except Exception as e:
        flash(f'Неожиданная ошибка: {str(e)}', 'error')
    
    return redirect(url_for('categories'))


@app.route('/categories/update/<int:category_id>', methods=['POST'])
@login_required
def update_category(category_id):
    try:
        user_id = session['user_id']
        name = escape(request.form.get('name', '').strip())
        limit_type = request.form.get('limit_type', '').strip()
        value_str = request.form.get('value', '').strip()
        
        if not name or not limit_type or not value_str:
            flash('Пожалуйста, заполните все поля', 'error')
            return redirect(url_for('categories'))
            
        if limit_type not in ['fixed', 'percent']:
            flash('Некорректный тип лимита', 'error')
            return redirect(url_for('categories'))
            
        value = validate_amount(value_str)
        
        def update_category_op(conn, user_id, category_id, name, limit_type, value):
            cursor = conn.execute('''
                UPDATE categories 
                SET name = ?, limit_type = ?, value = ?
                WHERE id = ? AND user_id = ?
            ''', (name, limit_type, float(value), category_id, user_id))
            return cursor.rowcount
            
        result = safe_db_operation(update_category_op, user_id, category_id, name, limit_type, value)
        
        if result > 0:
            flash(f'✓ Категория "{name}" обновлена!', 'success')
        else:
            flash('Категория не найдена', 'error')
            
    except ValueError as e:
        if "already exists" in str(e):
            flash('Категория с таким названием уже существует!', 'error')
        else:
            flash(f'Ошибка: {str(e)}', 'error')
    except Exception as e:
        flash(f'Неожиданная ошибка: {str(e)}', 'error')
    
    return redirect(url_for('categories'))


@app.route('/categories/delete/<int:category_id>', methods=['POST'])
@login_required
def delete_category(category_id):
    try:
        user_id = session['user_id']
        
        def delete_category_op(conn, user_id, category_id):
            cursor = conn.execute('DELETE FROM categories WHERE id = ? AND user_id = ?', (category_id, user_id))
            return cursor.rowcount
        
        result = safe_db_operation(delete_category_op, user_id, category_id)
        
        if result > 0:
            flash('✓ Категория удалена!', 'success')
        else:
            flash('Категория не найдена', 'error')
            
    except Exception as e:
        flash(f'Ошибка при удалении: {str(e)}', 'error')
    
    return redirect(url_for('categories'))


@app.route('/income')
@login_required
def income():
    user_id = session['user_id']
    conn = get_db()
    cursor = conn.execute('SELECT * FROM income WHERE user_id = ? ORDER BY month DESC', (user_id,))
    incomes = cursor.fetchall()
    conn.close()
    
    current_month = get_current_month()
    
    return render_template("income.html",
                         incomes=incomes, current_month=current_month)


@app.route('/income/add', methods=['POST'])
@login_required
def add_income():
    try:
        user_id = session['user_id']
        month = request.form.get('month', '').strip()
        amount_str = request.form.get('amount', '').strip()
        
        if not month or not amount_str:
            flash('Пожалуйста, заполните все поля', 'error')
            return redirect(url_for('income'))
            
        # Validate month format
        try:
            datetime.strptime(month, '%Y-%m')
        except ValueError:
            flash('Некорректный формат месяца', 'error')
            return redirect(url_for('income'))
            
        amount = validate_amount(amount_str)
        
        def add_income_op(conn, user_id, month, amount):
            cursor = conn.execute(
                'INSERT OR REPLACE INTO income (user_id, month, amount) VALUES (?, ?, ?)',
                (user_id, month, float(amount))
            )
            return cursor.rowcount
            
        result = safe_db_operation(add_income_op, user_id, month, amount)
        
        if result > 0:
            flash(f'✓ Доход за {month} сохранен: {amount} руб.', 'success')
        else:
            flash('Ошибка при сохранении дохода', 'error')
            
    except ValueError as e:
        flash(f'Ошибка: {str(e)}', 'error')
    except Exception as e:
        flash(f'Неожиданная ошибка: {str(e)}', 'error')
    
    return redirect(url_for('income'))


if __name__ == '__main__':
    # For testing: delete existing database to start fresh
    if os.environ.get('RESET_DB', '').lower() == 'true':
        if os.path.exists(DB_PATH):
            os.remove(DB_PATH)
            print(f"[RESET] Deleted existing database: {DB_PATH}")
    
    check_and_migrate_db()
    debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    app.run(host='0.0.0.0', port=5000, debug=debug_mode)