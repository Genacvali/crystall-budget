import os
import sqlite3
from datetime import datetime, date
from decimal import Decimal, ROUND_HALF_UP
from functools import wraps

from flask import (
    Flask, render_template, render_template_string, request, redirect,
    url_for, flash, session
)
from jinja2 import DictLoader, ChoiceLoader
from werkzeug.security import generate_password_hash, check_password_hash

# -----------------------------------------------------------------------------
# App config
# -----------------------------------------------------------------------------
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret")
DB_PATH = os.environ.get("BUDGET_DB", "budget.db")


# -----------------------------------------------------------------------------
# DB helpers
# -----------------------------------------------------------------------------
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_db()
    conn.executescript(
        """
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

        -- старая таблица income могла существовать (month-based)
        CREATE TABLE IF NOT EXISTS income (
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            month TEXT NOT NULL,
            amount REAL NOT NULL
        );

        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            date TEXT NOT NULL,             -- YYYY-MM-DD
            month TEXT NOT NULL,            -- YYYY-MM
            category_id INTEGER NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
            amount REAL NOT NULL,
            note TEXT
        );
        """
    )
    conn.commit()
    conn.close()


def migrate_income_to_daily_if_needed():
    """
    Если есть старая схема income (user_id, month, amount),
    переносим в новую income_daily с датой = month-01.
    """
    conn = get_db()
    cur = conn.cursor()

    # уже мигрировано?
    cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='income_daily'"
    )
    if cur.fetchone():
        conn.close()
        return

    # есть ли вообще income?
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='income'")
    if not cur.fetchone():
        # создаём сразу новую таблицу
        cur.executescript(
            """
            CREATE TABLE IF NOT EXISTS income_daily (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                date TEXT NOT NULL,   -- YYYY-MM-DD
                amount REAL NOT NULL
            );
            """
        )
        conn.commit()
        conn.close()
        return

    # проверим колонки
    cur.execute("PRAGMA table_info(income)")
    cols = [r[1] for r in cur.fetchall()]

    # создаём новую таблицу
    cur.executescript(
        """
        CREATE TABLE IF NOT EXISTS income_daily (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            date TEXT NOT NULL,   -- YYYY-MM-DD
            amount REAL NOT NULL
        );
        """
    )

    if "month" in cols and "amount" in cols:
        # переносим: month -> date = month-01
        cur.execute("SELECT user_id, month, amount FROM income")
        rows = cur.fetchall()
        for uid, month, amount in rows:
            if month and len(month) == 7:
                date_str = f"{month}-01"
            else:
                # на всякий случай — если формат другой, берём сегодня
                date_str = datetime.now().strftime("%Y-%m-01")
            cur.execute(
                "INSERT INTO income_daily (user_id, date, amount) VALUES (?, ?, ?)",
                (uid, date_str, amount),
            )

        # сохраним бэкап старой таблицы
        cur.executescript("ALTER TABLE income RENAME TO income_backup_monthly;")
        conn.commit()

    conn.close()


# -----------------------------------------------------------------------------
# Auth helpers
# -----------------------------------------------------------------------------
def login_required(f):
    @wraps(f)
    def _wrap(*args, **kwargs):
        if "user_id" not in session:
            flash("Войдите, чтобы продолжить", "error")
            return redirect(url_for("login"))
        return f(*args, **kwargs)

    return _wrap


# -----------------------------------------------------------------------------
# Jinja filters
# -----------------------------------------------------------------------------
def format_amount(value):
    try:
        v = Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        s = f"{v:,.2f}".replace(",", " ")
        if s.endswith("00"):
            # убираем .00, если целое
            return s[:-3]
        return s
    except Exception:
        return str(value)


def format_date_with_day(value):
    try:
        dt = datetime.strptime(value, "%Y-%m-%d")
        return dt.strftime("%d.%m.%Y")
    except Exception:
        return value


app.jinja_env.filters["format_amount"] = format_amount
app.jinja_env.filters["format_date_with_day"] = format_date_with_day


# -----------------------------------------------------------------------------
# Routes: auth
# -----------------------------------------------------------------------------
@app.route("/")
def index():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form["email"].lower().strip()
        name = request.form["name"].strip()
        password = request.form["password"]
        confirm = request.form["confirm"]

        if password != confirm:
            flash("Пароли не совпадают", "error")
            return render_template("register.html")

        conn = get_db()
        try:
            conn.execute(
                "INSERT INTO users(email, name, password_hash) VALUES (?,?,?)",
                (email, name, generate_password_hash(password)),
            )
            conn.commit()
            user = conn.execute(
                "SELECT id FROM users WHERE email=?", (email,)
            ).fetchone()
        except sqlite3.IntegrityError:
            flash("Email уже зарегистрирован", "error")
            conn.close()
            return render_template("register.html")
        conn.close()

        session["user_id"] = user["id"]
        session["email"] = email
        session["name"] = name
        return redirect(url_for("dashboard"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"].lower().strip()
        password = request.form["password"]

        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        conn.close()
        if user and check_password_hash(user["password_hash"], password):
            session["user_id"] = user["id"]
            session["email"] = user["email"]
            session["name"] = user["name"]
            return redirect(url_for("dashboard"))
        flash("Неверный email или пароль", "error")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# -----------------------------------------------------------------------------
# Routes: dashboard
# -----------------------------------------------------------------------------
@app.route("/dashboard")
@login_required
def dashboard():
    month = request.args.get("month") or datetime.now().strftime("%Y-%m")

    conn = get_db()
    uid = session["user_id"]

    # категории пользователя
    categories = conn.execute(
        "SELECT * FROM categories WHERE user_id=? ORDER BY name", (uid,)
    ).fetchall()

    # доход месяца из income_daily
    income_sum = conn.execute(
        """
        SELECT COALESCE(SUM(amount), 0)
        FROM income_daily
        WHERE user_id = ? AND strftime('%Y-%m', date) = ?
        """,
        (uid, month),
    ).fetchone()[0]

    # траты месяца
    expenses_rows = conn.execute(
        """
        SELECT e.id, e.date, e.amount, e.note, c.name as category_name
        FROM expenses e
        JOIN categories c ON c.id = e.category_id
        WHERE e.user_id = ? AND e.month = ?
        ORDER BY e.date DESC, e.id DESC
        """,
        (uid, month),
    ).fetchall()

    # сумма трат по категориям
    spent_by_cat = conn.execute(
        """
        SELECT c.id, c.name, COALESCE(SUM(e.amount), 0) as spent
        FROM categories c
        LEFT JOIN expenses e ON e.category_id = c.id AND e.user_id = c.user_id AND e.month = ?
        WHERE c.user_id = ?
        GROUP BY c.id, c.name
        """,
        (month, uid),
    ).fetchall()

    # расчёт лимитов категорий с учётом процента от дохода
    limits = conn.execute(
        "SELECT id, name, limit_type, value FROM categories WHERE user_id=?",
        (uid,),
    ).fetchall()

    data = []
    for row in limits:
        cat_id = row["id"]
        limit_val = 0.0
        if row["limit_type"] == "fixed":
            limit_val = float(row["value"])
        else:  # percent
            limit_val = float(income_sum) * float(row["value"]) / 100.0

        spent = 0.0
        for s in spent_by_cat:
            if s["id"] == cat_id:
                spent = float(s["spent"])
                break

        data.append(
            dict(category_name=row["name"], limit=limit_val, spent=spent)
        )

    conn.close()

    today = datetime.now().strftime("%Y-%m-%d")
    return render_template(
        "dashboard.html",
        categories=categories,
        expenses=expenses_rows,
        budget_data=data,
        income=income_sum,
        current_month=month,
        today=today,
        currency="RUB",
    )


@app.route("/quick-expense", methods=["POST"])
@login_required
def quick_expense():
    uid = session["user_id"]
    date_str = request.form.get("date", "").strip()
    category_id = request.form.get("category_id", "").strip()
    amount_str = request.form.get("amount", "").strip()
    note = (request.form.get("note") or "").strip()
    return_month = request.form.get("return_month") or datetime.now().strftime("%Y-%m")

    if not date_str or not category_id or not amount_str:
        flash("Пожалуйста, заполните все поля", "error")
        return redirect(url_for("dashboard", month=return_month))

    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        amount = float(amount_str)
        if amount <= 0:
            raise ValueError
    except Exception:
        flash("Неверные значения даты или суммы", "error")
        return redirect(url_for("dashboard", month=return_month))

    conn = get_db()
    conn.execute(
        """
        INSERT INTO expenses (user_id, date, month, category_id, amount, note)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (uid, date_str, date_str[:7], int(category_id), amount, note),
    )
    conn.commit()
    conn.close()
    flash("Расход добавлен", "success")
    return redirect(url_for("dashboard", month=return_month))


# -----------------------------------------------------------------------------
# Routes: categories
# -----------------------------------------------------------------------------
@app.route("/categories")
@login_required
def categories():
    uid = session["user_id"]
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM categories WHERE user_id=? ORDER BY name", (uid,)
    ).fetchall()
    conn.close()
    return render_template("categories.html", categories=rows)


@app.route("/categories/add", methods=["POST"])
@login_required
def categories_add():
    uid = session["user_id"]
    name = (request.form.get("name") or "").strip()
    limit_type = request.form.get("limit_type")
    value = request.form.get("value")

    if not name or not limit_type or not value:
        flash("Пожалуйста, заполните все поля", "error")
        return redirect(url_for("categories"))

    try:
        val = float(value)
        if val <= 0:
            raise ValueError
    except Exception:
        flash("Введите корректное значение лимита", "error")
        return redirect(url_for("categories"))

    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO categories (user_id, name, limit_type, value) VALUES (?,?,?,?)",
            (uid, name, limit_type, val),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        flash("Категория с таким названием уже существует", "error")
    finally:
        conn.close()

    flash("Категория добавлена", "success")
    return redirect(url_for("categories"))


@app.route("/categories/update/<int:cat_id>", methods=["POST"])
@login_required
def categories_update(cat_id):
    uid = session["user_id"]
    name = (request.form.get("name") or "").strip()
    limit_type = request.form.get("limit_type")
    value = request.form.get("value")

    if not name or not limit_type or not value:
        flash("Пожалуйста, заполните все поля", "error")
        return redirect(url_for("categories"))

    try:
        val = float(value)
        if val <= 0:
            raise ValueError
    except Exception:
        flash("Введите корректное значение лимита", "error")
        return redirect(url_for("categories"))

    conn = get_db()
    conn.execute(
        """
        UPDATE categories
           SET name=?, limit_type=?, value=?
         WHERE id=? AND user_id=?
        """,
        (name, limit_type, val, cat_id, uid),
    )
    conn.commit()
    conn.close()
    flash("Категория обновлена", "success")
    return redirect(url_for("categories"))


@app.route("/categories/delete/<int:cat_id>", methods=["POST"])
@login_required
def categories_delete(cat_id):
    uid = session["user_id"]
    conn = get_db()
    conn.execute("DELETE FROM categories WHERE id=? AND user_id=?", (cat_id, uid))
    conn.commit()
    conn.close()
    flash("Категория удалена", "success")
    return redirect(url_for("categories"))


# -----------------------------------------------------------------------------
# Routes: expenses
# -----------------------------------------------------------------------------
@app.route("/expenses", methods=["GET", "POST"])
@login_required
def expenses():
    uid = session["user_id"]

    if request.method == "POST":
        date_str = (request.form.get("date") or "").strip()
        category_id = request.form.get("category_id")
        amount_str = (request.form.get("amount") or "").strip()
        note = (request.form.get("note") or "").strip()

        if not date_str or not category_id or not amount_str:
            flash("Пожалуйста, заполните все поля", "error")
            return redirect(url_for("expenses"))

        try:
            datetime.strptime(date_str, "%Y-%m-%d")
            amount = float(amount_str)
            if amount <= 0:
                raise ValueError
        except Exception:
            flash("Неверные значения даты или суммы", "error")
            return redirect(url_for("expenses"))

        conn = get_db()
        conn.execute(
            """
            INSERT INTO expenses (user_id, date, month, category_id, amount, note)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (uid, date_str, date_str[:7], int(category_id), amount, note),
        )
        conn.commit()
        conn.close()
        flash("Расход добавлен", "success")
        return redirect(url_for("expenses"))

    # GET
    conn = get_db()
    cats = conn.execute(
        "SELECT id, name FROM categories WHERE user_id=? ORDER BY name", (uid,)
    ).fetchall()
    rows = conn.execute(
        """
        SELECT e.id, e.date, e.amount, e.note, c.name AS category_name
        FROM expenses e
        JOIN categories c ON c.id = e.category_id
        WHERE e.user_id = ?
        ORDER BY e.date DESC, e.id DESC
        """,
        (uid,),
    ).fetchall()
    conn.close()
    today = datetime.now().strftime("%Y-%m-%d")
    return render_template("expenses.html", categories=cats, expenses=rows, today=today)


@app.route("/expenses/delete/<int:expense_id>", methods=["POST"])
@login_required
def delete_expense(expense_id):
    uid = session["user_id"]
    conn = get_db()
    conn.execute("DELETE FROM expenses WHERE id=? AND user_id=?", (expense_id, uid))
    conn.commit()
    conn.close()
    flash("Расход удалён", "success")
    return redirect(url_for("expenses"))


# -----------------------------------------------------------------------------
# Routes: income (daily)
# -----------------------------------------------------------------------------
@app.route("/income")
@login_required
def income_page():
    uid = session["user_id"]
    conn = get_db()
    rows = conn.execute(
        """
        SELECT id, date, amount
        FROM income_daily
        WHERE user_id = ?
        ORDER BY date DESC, id DESC
        """,
        (uid,),
    ).fetchall()
    conn.close()
    today = datetime.now().strftime("%Y-%m-%d")
    return render_template("income.html", incomes=rows, today=today)


@app.route("/income/add", methods=["POST"])
@login_required
def income_add():
    uid = session["user_id"]
    date_str = (request.form.get("date") or "").strip()
    amount_str = (request.form.get("amount") or "").strip()

    if not date_str or not amount_str:
        flash("Пожалуйста, заполните все поля", "error")
        return redirect(url_for("income_page"))

    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        amount = float(amount_str)
        if amount <= 0:
            raise ValueError
    except Exception:
        flash("Неверные значения даты или суммы", "error")
        return redirect(url_for("income_page"))

    conn = get_db()
    conn.execute(
        "INSERT INTO income_daily (user_id, date, amount) VALUES (?,?,?)",
        (uid, date_str, amount),
    )
    conn.commit()
    conn.close()
    flash("Доход добавлен", "success")
    return redirect(url_for("income_page"))


@app.route("/income/edit/<int:income_id>", methods=["GET", "POST"])
@login_required
def edit_income(income_id):
    uid = session["user_id"]
    conn = get_db()
    row = conn.execute(
        "SELECT id, date, amount FROM income_daily WHERE id=? AND user_id=?",
        (income_id, uid),
    ).fetchone()
    if not row:
        conn.close()
        flash("Запись не найдена", "error")
        return redirect(url_for("income_page"))

    if request.method == "POST":
        date_str = (request.form.get("date") or "").strip()
        amount_str = (request.form.get("amount") or "").strip()
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
            amount = float(amount_str)
            if amount <= 0:
                raise ValueError
        except Exception:
            flash("Неверные значения даты или суммы", "error")
            return redirect(url_for("edit_income", income_id=income_id))

        conn.execute(
            "UPDATE income_daily SET date=?, amount=? WHERE id=? AND user_id=?",
            (date_str, amount, income_id, uid),
        )
        conn.commit()
        conn.close()
        flash("Доход обновлён", "success")
        return redirect(url_for("income_page"))

    conn.close()
    # простой шаблон редактирования (inline)
    return render_template_string(
        """
        {% extends "base.html" %}
        {% block title %}Редактировать доход{% endblock %}
        {% block content %}
        <div class="container" style="max-width:560px">
          <h3 class="mb-3">Редактировать доход</h3>
          <form method="post">
            <div class="mb-3">
              <label class="form-label">Дата</label>
              <input class="form-control" type="date" name="date" value="{{ income.date }}" required>
            </div>
            <div class="mb-3">
              <label class="form-label">Сумма</label>
              <input class="form-control" type="number" name="amount" step="0.01" min="0.01" value="{{ income.amount }}" required>
            </div>
            <div class="d-flex gap-2">
              <button class="btn btn-primary">Сохранить</button>
              <a class="btn btn-secondary" href="{{ url_for('income_page') }}">Отмена</a>
            </div>
          </form>
        </div>
        {% endblock %}
        """,
        income=row,
    )


@app.route("/income/delete/<int:income_id>", methods=["POST"])
@login_required
def delete_income(income_id):
    uid = session["user_id"]
    conn = get_db()
    conn.execute("DELETE FROM income_daily WHERE id=? AND user_id=?", (income_id, uid))
    conn.commit()
    conn.close()
    flash("Доход удалён", "success")
    return redirect(url_for("income_page"))


# -----------------------------------------------------------------------------
# Templates (DictLoader)
# -----------------------------------------------------------------------------
BASE_HTML = """
<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{% block title %}CrystalBudget{% endblock %}</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
  <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.css" rel="stylesheet">
  <style>
    body { background-color: #f6f7f9; }
    .navbar-brand { font-weight: 600; }
    .modern-card { border: 1px solid #e9ecef; border-radius: .75rem; background: #fff; }
    .card-grid { display: grid; gap: 1rem; grid-template-columns: repeat(auto-fill,minmax(240px,1fr)); }
    .table-modern thead th { background:#f8f9fa; }
    .badge-modern { padding:.35rem .6rem; border-radius:.5rem; font-size:.8rem; }
    .badge-modern-success { background:#e8f6ee; color:#0f5132; }
    .badge-modern-warning { background:#fff4e5; color:#664d03; }
    .badge-modern-danger { background:#fdecea; color:#842029; }
    .container { max-width: 1100px; }
    /* селекты вниз */
    select.form-select, .form-modern { position:relative; overflow:hidden; z-index:1; }
    select.form-select option, .form-modern option { position:relative; z-index:9999; }
  </style>
</head>
<body>
  <nav class="navbar navbar-dark bg-dark">
    <div class="container">
      <a class="navbar-brand" href="{{ url_for('dashboard') }}">💎 CrystalBudget</a>
      <div class="d-flex gap-2">
        {% if session.get('user_id') %}
          <a class="btn btn-sm btn-outline-light" href="{{ url_for('dashboard') }}">Дашборд</a>
          <a class="btn btn-sm btn-outline-light" href="{{ url_for('expenses') }}">Траты</a>
          <a class="btn btn-sm btn-outline-light" href="{{ url_for('categories') }}">Категории</a>
          <a class="btn btn-sm btn-outline-light" href="{{ url_for('income_page') }}">Доходы</a>
          <a class="btn btn-sm btn-warning" href="{{ url_for('logout') }}">Выйти</a>
        {% else %}
          <a class="btn btn-sm btn-outline-light" href="{{ url_for('login') }}">Войти</a>
          <a class="btn btn-sm btn-primary" href="{{ url_for('register') }}">Регистрация</a>
        {% endif %}
      </div>
    </div>
  </nav>
  <div class="container my-4">
    {% with messages = get_flashed_messages(with_categories=true) %}
      {% if messages %}
        {% for cat, msg in messages %}
          <div class="alert alert-{{ 'danger' if cat=='error' else cat }} alert-dismissible fade show" role="alert">
            {{ msg }}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
          </div>
        {% endfor %}
      {% endif %}
    {% endwith %}
    {% block content %}{% endblock %}
  </div>
  <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
  {% block scripts %}{% endblock %}
</body>
</html>
"""

LOGIN_HTML = """
{% extends "base.html" %}
{% block title %}Вход — CrystalBudget{% endblock %}
{% block content %}
<div class="container" style="max-width:420px;">
  <h3 class="mb-3">Вход</h3>
  <form method="post">
    <div class="mb-3">
      <label class="form-label">Email</label>
      <input class="form-control" type="email" name="email" required>
    </div>
    <div class="mb-3">
      <label class="form-label">Пароль</label>
      <input class="form-control" type="password" name="password" required>
    </div>
    <button class="btn btn-primary w-100">Войти</button>
  </form>
  <div class="text-center mt-3">
    <a href="{{ url_for('register') }}">Создать аккаунт</a>
  </div>
</div>
{% endblock %}
"""

REGISTER_HTML = """
{% extends "base.html" %}
{% block title %}Регистрация — CrystalBudget{% endblock %}
{% block content %}
<div class="container" style="max-width:520px;">
  <h3 class="mb-3">Регистрация</h3>
  <form method="post">
    <div class="mb-3">
      <label class="form-label">Имя</label>
      <input class="form-control" name="name" required>
    </div>
    <div class="mb-3">
      <label class="form-label">Email</label>
      <input class="form-control" type="email" name="email" required>
    </div>
    <div class="mb-3">
      <label class="form-label">Пароль</label>
      <input class="form-control" type="password" name="password" required>
    </div>
    <div class="mb-3">
      <label class="form-label">Повторите пароль</label>
      <input class="form-control" type="password" name="confirm" required>
    </div>
    <button class="btn btn-success w-100">Создать аккаунт</button>
  </form>
  <div class="text-center mt-3">
    <a href="{{ url_for('login') }}">У меня уже есть аккаунт</a>
  </div>
</div>
{% endblock %}
"""

# Дашборд — компактная версия (кнопка "Добавить" адаптивная, нейтральная иконка калькулятора)
DASHBOARD_HTML = """
{% extends "base.html" %}
{% block title %}📊 Дашборд — CrystalBudget{% endblock %}

{% block content %}
<style>
.quick-add-btn { min-height: 42px; display:inline-flex; align-items:center; justify-content:center; white-space:nowrap; }
.quick-add-text { display:none; } @media (min-width:768px){ .quick-add-text{ display:inline; } }
</style>

<div class="d-flex flex-column flex-md-row justify-content-between align-items-start align-items-md-center mb-4 gap-3">
  <div>
    <h1 class="m-0 d-flex align-items-center gap-2"><i class="bi bi-speedometer2"></i> Финансовый дашборд</h1>
    <p class="text-secondary mb-0">Управляйте своим бюджетом эффективно</p>
  </div>
  <form method="get" class="d-flex align-items-center gap-2">
    <i class="bi bi-calendar3 text-primary"></i>
    <input type="month" name="month" value="{{ current_month }}" class="form-control form-control-sm" style="max-width: 180px;">
    <button class="btn btn-outline-primary btn-sm">Показать</button>
  </form>
</div>

<div class="modern-card mb-4">
  <div class="card-body">
    <div class="d-flex align-items-center justify-content-between mb-3">
      <h5 class="m-0"><i class="bi bi-plus-circle-fill"></i> Быстрое добавление расхода</h5>
      <button class="btn btn-sm btn-outline-secondary" type="button" data-bs-toggle="collapse" data-bs-target="#quickAddForm"><i class="bi bi-chevron-down"></i></button>
    </div>

    <div class="collapse show" id="quickAddForm">
      <form method="POST" action="/quick-expense" class="quick-expense-form">
        <input type="hidden" name="return_month" value="{{ current_month }}">
        <div class="row g-3">
          <div class="col-12 col-md-3">
            <label class="form-label"><i class="bi bi-calendar3"></i> Дата</label>
            <input type="date" name="date" value="{{ today }}" class="form-control" required>
          </div>
          <div class="col-12 col-md-3">
            <label class="form-label"><i class="bi bi-tags-fill"></i> Категория</label>
            <div class="d-flex gap-2">
              <select name="category_id" class="form-select" required style="flex:1;">
                <option value="">Выберите категорию…</option>
                {% for cat in categories %}
                <option value="{{ cat.id }}">{{ cat.name }}</option>
                {% endfor %}
              </select>
              <a class="btn btn-outline-secondary" href="{{ url_for('categories') }}" title="Создать категорию"><i class="bi bi-plus"></i></a>
            </div>
          </div>
          <div class="col-12 col-md-2">
            <label class="form-label"><i class="bi bi-calculator"></i> Сумма</label>
            <input type="number" name="amount" placeholder="0.00" step="0.01" min="0.01" inputmode="decimal" class="form-control" required>
          </div>
          <div class="col-12 col-md-3">
            <label class="form-label"><i class="bi bi-chat-dots-fill"></i> Комментарий</label>
            <input type="text" name="note" placeholder="Описание (необязательно)" class="form-control">
          </div>
          <div class="col-12 col-md-auto d-flex align-items-center justify-content-end">
            <button type="submit" class="btn btn-success quick-add-btn w-100 w-md-auto px-3">
              <i class="bi bi-plus-lg me-1"></i> <span class="quick-add-text">Добавить</span>
            </button>
          </div>
        </div>
      </form>
    </div>
  </div>
</div>

{% if budget_data %}
<div class="card-grid mb-4">
  {% for item in budget_data %}
  {% set progress_percent = (item.limit > 0 and (item.spent / item.limit * 100) or 0) | round(1) %}
  {% set rest = item.limit - item.spent %}
  <div class="modern-card">
    <div class="card-body">
      <div class="d-flex justify-content-between align-items-center mb-3">
        <h6 class="fw-bold text-primary m-0">{{ item.category_name }}</h6>
        <div class="d-flex align-items-center gap-2">
          <small class="text-muted">{{ progress_percent }}%</small>
          <div class="progress" style="width:80px; height:6px;">
            <div class="progress-bar {% if progress_percent < 50 %}bg-success{% elif progress_percent < 80 %}bg-warning{% else %}bg-danger{% endif %}" style="width: {{ [progress_percent, 100] | min }}%;"></div>
          </div>
        </div>
      </div>
      <div class="row g-2 text-center">
        <div class="col-6">
          <div class="p-2 rounded" style="background:#f8f9fa;">
            <small class="text-muted d-block">Лимит</small>
            <strong class="text-primary">{{ item.limit|format_amount }} ₽</strong>
          </div>
        </div>
        <div class="col-6">
          <div class="p-2 rounded" style="background:#f8f9fa;">
            <small class="text-muted d-block">Потрачено</small>
            <strong class="{% if rest < 0 %}text-danger{% else %}text-success{% endif %}">{{ item.spent|format_amount }} ₽</strong>
          </div>
        </div>
      </div>
      <div class="mt-3 text-center">
        <small class="text-muted">Остаток:</small>
        <div class="fs-5 fw-bold {% if rest < 0 %}text-danger{% else %}text-success{% endif %}">{{ rest|format_amount }} ₽</div>
      </div>
    </div>
  </div>
  {% endfor %}
</div>
{% endif %}
{% endblock %}
"""

CATEGORIES_HTML = """
{% extends "base.html" %}
{% block title %}Категории — CrystalBudget{% endblock %}
{% block content %}
<style>
select.form-select{position:relative;overflow:hidden;z-index:1}
select.form-select option{position:relative;z-index:9999}
</style>

<div class="d-flex justify-content-between align-items-center mb-3">
  <h2 class="h4 m-0">Категории</h2>
  <button class="btn btn-primary" data-bs-toggle="collapse" data-bs-target="#addCategoryForm">
    <i class="bi bi-plus-lg me-1"></i> Добавить категорию
  </button>
</div>

<div class="collapse mb-3" id="addCategoryForm">
  <div class="card card-body">
    <form method="POST" action="/categories/add">
      <div class="row g-3">
        <div class="col-md-4">
          <label class="form-label">Название</label>
          <input type="text" name="name" class="form-control" placeholder="Например, Продукты" required>
        </div>
        <div class="col-md-3">
          <label class="form-label">Тип лимита</label>
          <select name="limit_type" class="form-select" required>
            <option value="fixed">Фиксированная сумма</option>
            <option value="percent">Процент от дохода</option>
          </select>
        </div>
        <div class="col-md-3">
          <label class="form-label">Значение</label>
          <input type="number" name="value" step="0.01" min="0.01" inputmode="decimal" class="form-control" placeholder="Сумма или %" required>
        </div>
        <div class="col-md-2 d-grid">
          <label class="form-label d-none d-md-block">&nbsp;</label>
          <button class="btn btn-success">Сохранить</button>
        </div>
      </div>
    </form>
  </div>
</div>

<!-- Мобильные карточки -->
<div class="d-block d-md-none">
  {% for cat in categories %}
  <div class="card mb-2">
    <div class="card-body">
      <form method="POST" action="/categories/update/{{ cat.id }}">
        <div class="row g-2">
          <div class="col-12">
            <label class="form-label">Название</label>
            <input type="text" name="name" value="{{ cat.name }}" class="form-control" required>
          </div>
          <div class="col-6">
            <label class="form-label">Тип</label>
            <select name="limit_type" class="form-select">
              <option value="fixed" {% if cat.limit_type == 'fixed' %}selected{% endif %}>Фиксированная сумма</option>
              <option value="percent" {% if cat.limit_type == 'percent' %}selected{% endif %}>Процент от дохода</option>
            </select>
          </div>
          <div class="col-6">
            <label class="form-label">Значение</label>
            <input type="number" name="value" value="{{ cat.value }}" step="0.01" min="0.01" inputmode="decimal" class="form-control" required>
          </div>
          <div class="col-12 d-flex gap-2">
            <button class="btn btn-outline-primary flex-fill"><i class="bi bi-check-lg me-1"></i> Обновить</button>
            <button type="button" class="btn btn-outline-danger flex-fill" onclick="if(confirm('Удалить категорию «{{ cat.name }}»?')){ const f=document.createElement('form'); f.method='POST'; f.action='/categories/delete/{{ cat.id }}'; document.body.appendChild(f); f.submit(); }">
              <i class="bi bi-trash3 me-1"></i> Удалить
            </button>
          </div>
        </div>
      </form>
    </div>
  </div>
  {% endfor %}
</div>

<!-- Таблица -->
<div class="table-responsive d-none d-md-block">
  <table class="table align-middle">
    <thead class="table-light">
      <tr>
        <th>Название</th>
        <th>Тип лимита</th>
        <th class="text-end">Значение</th>
        <th class="text-end">Действия</th>
      </tr>
    </thead>
    <tbody>
      {% for cat in categories %}
      <tr>
        <form method="POST" action="/categories/update/{{ cat.id }}" class="d-contents">
          <td style="min-width:220px">
            <input type="text" name="name" value="{{ cat.name }}" class="form-control form-control-sm" required>
          </td>
          <td style="min-width:180px">
            <select name="limit_type" class="form-select form-select-sm">
              <option value="fixed" {% if cat.limit_type == 'fixed' %}selected{% endif %}>Фиксированная сумма</option>
              <option value="percent" {% if cat.limit_type == 'percent' %}selected{% endif %}>Процент от дохода</option>
            </select>
          </td>
          <td class="text-end" style="min-width:160px">
            <input type="number" name="value" value="{{ cat.value }}" step="0.01" min="0.01" inputmode="decimal" class="form-control form-control-sm text-end" required>
          </td>
          <td class="text-end" style="min-width:200px">
            <div class="btn-group btn-group-sm">
              <button class="btn btn-outline-primary"><i class="bi bi-check-lg me-1"></i> Сохранить</button>
        </form>
              <form method="POST" action="/categories/delete/{{ cat.id }}" class="d-inline">
                <button class="btn btn-outline-danger" onclick="return confirm('Удалить категорию?')"><i class="bi bi-trash3 me-1"></i> Удалить</button>
              </form>
            </div>
          </td>
      </tr>
      {% endfor %}
    </tbody>
  </table>
</div>

{% if not categories %}
<div class="text-center py-5">
  <p class="text-muted mb-3">Категории не созданы</p>
  <button class="btn btn-primary" data-bs-toggle="collapse" data-bs-target="#addCategoryForm"><i class="bi bi-plus-lg me-1"></i> Создать категорию</button>
</div>
{% endif %}
{% endblock %}
"""

EXPENSES_HTML = """
{% extends "base.html" %}
{% block title %}Расходы — CrystalBudget{% endblock %}

{% block content %}
<div class="d-flex justify-content-between align-items-center mb-3">
  <h2 class="h4 m-0">Мои расходы</h2>
  <button class="btn btn-primary" data-bs-toggle="collapse" data-bs-target="#addExpenseForm">
    <i class="bi bi-plus-lg me-1"></i> Добавить расход
  </button>
</div>

<div class="collapse mb-3" id="addExpenseForm">
  <div class="card card-body">
    <form method="POST" action="/expenses">
      <div class="row g-3">
        <div class="col-md-3">
          <label class="form-label">Дата</label>
          <input type="date" name="date" value="{{ today }}" class="form-control" required>
        </div>
        <div class="col-md-3">
          <label class="form-label">Категория</label>
          <select name="category_id" class="form-select" required>
            <option value="">Выберите категорию</option>
            {% for cat in categories %}
            <option value="{{ cat.id }}">{{ cat.name }}</option>
            {% endfor %}
          </select>
        </div>
        <div class="col-md-2">
          <label class="form-label">Сумма</label>
          <input type="number" name="amount" step="0.01" min="0.01" inputmode="decimal" class="form-control" required>
        </div>
        <div class="col-md-3">
          <label class="form-label">Комментарий</label>
          <input type="text" name="note" class="form-control">
        </div>
        <div class="col-md-1 d-grid">
          <label class="form-label d-none d-md-block">&nbsp;</label>
          <button class="btn btn-success">Добавить</button>
        </div>
      </div>
    </form>
  </div>
</div>

<!-- Мобильные карточки -->
<div class="d-block d-md-none">
  {% for e in expenses %}
  <div class="card mb-2">
    <div class="card-body">
      <div class="d-flex justify-content-between align-items-start mb-2">
        <div>
          <h6 class="mb-1">{{ e.amount|format_amount }} ₽</h6>
          <small class="text-muted"><i class="bi bi-calendar3"></i> {{ e.date|format_date_with_day }}</small>
        </div>
        <span class="badge text-bg-secondary">{{ e.category_name }}</span>
      </div>
      {% if e.note %}<div class="text-muted mb-2">{{ e.note }}</div>{% endif %}
      <form method="POST" action="{{ url_for('delete_expense', expense_id=e.id) }}">
        <button class="btn btn-outline-danger w-100" onclick="return confirm('Удалить расход?\\nДата: {{ e.date|format_date_with_day }}\\nКатегория: {{ e.category_name }}\\nСумма: {{ e.amount|format_amount }} ₽')">
          <i class="bi bi-trash"></i> Удалить
        </button>
      </form>
    </div>
  </div>
  {% endfor %}
</div>

<!-- Табличный вид -->
<div class="table-responsive d-none d-md-block">
  <table class="table table-striped align-middle">
    <thead class="table-light">
      <tr>
        <th>Дата</th>
        <th>Категория</th>
        <th class="text-end">Сумма</th>
        <th>Комментарий</th>
        <th class="text-end">Действия</th>
      </tr>
    </thead>
    <tbody>
      {% for e in expenses %}
      <tr>
        <td>{{ e.date|format_date_with_day }}</td>
        <td>{{ e.category_name }}</td>
        <td class="text-end fw-bold">{{ e.amount|format_amount }} ₽</td>
        <td>{{ e.note or '' }}</td>
        <td class="text-end">
          <form method="POST" action="{{ url_for('delete_expense', expense_id=e.id) }}" class="d-inline">
            <button class="btn btn-sm btn-outline-danger" onclick="return confirm('Удалить расход?\\nДата: {{ e.date|format_date_with_day }}\\nКатегория: {{ e.category_name }}\\nСумма: {{ e.amount|format_amount }} ₽')">
              <i class="bi bi-trash"></i> Удалить
            </button>
          </form>
        </td>
      </tr>
      {% endfor %}
    </tbody>
  </table>
</div>

{% if not expenses %}
<div class="text-center py-5">
  <p class="text-muted mb-3">Расходов пока нет</p>
  <button class="btn btn-primary" data-bs-toggle="collapse" data-bs-target="#addExpenseForm"><i class="bi bi-plus-lg me-1"></i> Добавить первый расход</button>
</div>
{% endif %}
{% endblock %}
"""

INCOME_HTML = """
{% extends "base.html" %}
{% block title %}Доходы — CrystalBudget{% endblock %}

{% block content %}
<div class="d-flex justify-content-between align-items-center mb-3">
  <h2 class="h4 m-0">Мои доходы</h2>
</div>

<form method="POST" action="{{ url_for('income_add') }}" class="mb-3">
  <div class="card card-body">
    <div class="row g-3">
      <div class="col-md-4">
        <label class="form-label">Дата</label>
        <input type="date" id="date" name="date" value="{{ today }}" class="form-control" required>
      </div>
      <div class="col-md-4">
        <label class="form-label">Сумма</label>
        <input type="number" id="amount" name="amount" step="0.01" min="0.01" inputmode="decimal" class="form-control" placeholder="Сумма дохода" required>
      </div>
      <div class="col-md-4 d-grid">
        <label class="form-label d-none d-md-block">&nbsp;</label>
        <button class="btn btn-success">Добавить доход</button>
      </div>
    </div>
  </div>
</form>

<!-- Мобильный вид -->
<div class="d-block d-md-none">
  {% for income in incomes %}
  <div class="card mb-2">
    <div class="card-body">
      <div class="d-flex justify-content-between align-items-start mb-2">
        <div>
          <h6 class="mb-1">{{ income.amount|format_amount }} ₽</h6>
          <small class="text-muted"><i class="bi bi-calendar3"></i> {{ income.date|format_date_with_day }}</small>
        </div>
      </div>
      <div class="d-flex gap-2 mt-2">
        <a href="{{ url_for('edit_income', income_id=income.id) }}" class="btn btn-outline-primary flex-fill"><i class="bi bi-pencil"></i> Изменить</a>
        <form method="POST" action="{{ url_for('delete_income', income_id=income.id) }}" class="flex-fill">
          <button class="btn btn-outline-danger w-100" onclick="return confirm('Удалить доход?\\nДата: {{ income.date|format_date_with_day }}\\nСумма: {{ income.amount|format_amount }}₽')">
            <i class="bi bi-trash"></i> Удалить
          </button>
        </form>
      </div>
    </div>
  </div>
  {% endfor %}
</div>

<!-- Таблица -->
<div class="table-responsive d-none d-md-block">
  <table class="table table-striped align-middle">
    <thead class="table-light">
      <tr>
        <th>Дата</th>
        <th class="text-end">Сумма</th>
        <th class="text-end">Действия</th>
      </tr>
    </thead>
    <tbody>
      {% for income in incomes %}
      <tr>
        <td>{{ income.date|format_date_with_day }}</td>
        <td class="text-end fw-bold">{{ income.amount|format_amount }} ₽</td>
        <td class="text-end">
          <a href="{{ url_for('edit_income', income_id=income.id) }}" class="btn btn-sm btn-outline-primary me-1"><i class="bi bi-pencil"></i> Изменить</a>
          <form method="POST" action="{{ url_for('delete_income', income_id=income.id) }}" class="d-inline">
            <button class="btn btn-sm btn-outline-danger" onclick="return confirm('Удалить доход?\\nДата: {{ income.date|format_date_with_day }}\\nСумма: {{ income.amount|format_amount }}₽')">
              <i class="bi bi-trash"></i> Удалить
            </button>
          </form>
        </td>
      </tr>
      {% endfor %}
    </tbody>
  </table>
</div>

{% if not incomes %}
<div class="text-center py-5">
  <p class="text-muted mb-3">Доходов пока нет</p>
  <button class="btn btn-primary" onclick="document.getElementById('date')?.focus()"><i class="bi bi-plus-lg me-1"></i> Добавить первый доход</button>
</div>
{% endif %}
{% endblock %}

{% block scripts %}
<script>
document.addEventListener('DOMContentLoaded', function() {
  const dateInput = document.getElementById('date');
  if (dateInput && !dateInput.value) {
    const now = new Date();
    dateInput.value = now.toISOString().slice(0, 10);
  }
});
</script>
{% endblock %}
"""

app.jinja_loader = ChoiceLoader(
    [
        DictLoader(
            {
                "base.html": BASE_HTML,
                "login.html": LOGIN_HTML,
                "register.html": REGISTER_HTML,
                "dashboard.html": DASHBOARD_HTML,
                "categories.html": CATEGORIES_HTML,
                "expenses.html": EXPENSES_HTML,
                "income.html": INCOME_HTML,
            }
        ),
        app.jinja_loader,
    ]
)

# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    init_db()
    migrate_income_to_daily_if_needed()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
