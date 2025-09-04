import os
import sqlite3
from datetime import datetime
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
@app.template_filter("format_amount")
def format_amount(value):
    try:
        value = float(value)
    except (ValueError, TypeError):
        return value
    # Если целое — убираем .0
    if value.is_integer():
        return f"{int(value):,}".replace(",", " ")
    return f"{value:,.2f}".replace(",", " ")
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
    income_exists = cur.fetchone() is not None

    # создаём новую таблицу (если нет)
    cur.executescript(
        """
        CREATE TABLE IF NOT EXISTS income_daily (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            date TEXT NOT NULL,   -- YYYY-MM-DD
            amount REAL NOT NULL,
            source_id INTEGER REFERENCES income_sources(id)
        );
        """
    )

    if income_exists:
        # проверим колонки старой income
        cur.execute("PRAGMA table_info(income)")
        cols = [r[1] for r in cur.fetchall()]

        if "month" in cols and "amount" in cols:
            # переносим: month -> date = month-01
            cur.execute("SELECT user_id, month, amount FROM income")
            rows = cur.fetchall()
            for uid, month, amount in rows:
                if month and len(month) == 7:
                    date_str = f"{month}-01"
                else:
                    date_str = datetime.now().strftime("%Y-%m-01")
                cur.execute(
                    "INSERT INTO income_daily (user_id, date, amount) VALUES (?, ?, ?)",
                    (uid, date_str, amount),
                )
            # сохраним бэкап старой таблицы
            cur.executescript("ALTER TABLE income RENAME TO income_backup_monthly;")

    conn.commit()
    conn.close()


def ensure_income_sources_tables():
    """Создаём таблицы источников и правил, если их нет."""
    conn = get_db()
    cur = conn.cursor()
    # таблица источников доходов
    cur.execute("""
    CREATE TABLE IF NOT EXISTS income_sources (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
      name TEXT NOT NULL,
      is_default INTEGER NOT NULL DEFAULT 0,
      UNIQUE(user_id, name)
    )
    """)
    # таблица правил маршрутизации расходов
    cur.execute("""
    CREATE TABLE IF NOT EXISTS source_category_rules (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
      source_id INTEGER NOT NULL REFERENCES income_sources(id) ON DELETE CASCADE,
      category_id INTEGER NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
      priority INTEGER NOT NULL DEFAULT 100,
      UNIQUE(user_id, category_id)
    )
    """)
    conn.commit()
    conn.close()


def add_source_id_column_if_missing():
    """Добавляет колонку source_id в income_daily, если её нет."""
    conn = get_db()
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(income_daily)")
    cols = [r[1] for r in cur.fetchall()]
    if "source_id" not in cols:
        try:
            cur.execute("ALTER TABLE income_daily ADD COLUMN source_id INTEGER REFERENCES income_sources(id)")
            conn.commit()
        except sqlite3.OperationalError:
            pass
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
# Helpers: sources & rules
# -----------------------------------------------------------------------------
def get_default_source_id(conn, user_id):
    row = conn.execute(
        "SELECT id FROM income_sources WHERE user_id=? AND is_default=1",
        (user_id,)
    ).fetchone()
    return row["id"] if row else None


def get_source_for_category(conn, user_id, category_id):
    row = conn.execute(
        "SELECT source_id FROM source_category_rules WHERE user_id=? AND category_id=?",
        (user_id, category_id)
    ).fetchone()
    return row["source_id"] if row else None


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

    # траты месяца (для списка)
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
            dict(category_name=row["name"], limit=limit_val, spent=spent, id=cat_id)
        )

    # ---- НОВОЕ: балансы по источникам в выбранном месяце ----
    sources = conn.execute(
        "SELECT id, name FROM income_sources WHERE user_id=? ORDER BY name", (uid,)
    ).fetchall()

    # приход по источнику
    income_by_source = {
        s["id"]: conn.execute(
            """
            SELECT COALESCE(SUM(amount),0) FROM income_daily
            WHERE user_id=? AND source_id=? AND strftime('%Y-%m', date)=?
            """,
            (uid, s["id"], month),
        ).fetchone()[0]
        for s in sources
    }

    # правило категория->источник
    rule_rows = conn.execute(
        "SELECT category_id, source_id FROM source_category_rules WHERE user_id=?",
        (uid,),
    ).fetchall()
    rule_map = {r["category_id"]: r["source_id"] for r in rule_rows}

    # расход по источнику (по правилам)
    expense_by_source = {s["id"]: 0.0 for s in sources}
    for cat in limits:
        cat_id = cat["id"]
        src_id = rule_map.get(cat_id)
        if not src_id:
            continue
        spent_val = conn.execute(
            """
            SELECT COALESCE(SUM(amount),0) FROM expenses
            WHERE user_id=? AND month=? AND category_id=?
            """,
            (uid, month, cat_id),
        ).fetchone()[0]
        expense_by_source[src_id] += float(spent_val)

    source_balances = []
    for s in sources:
        sid = s["id"]
        inc = float(income_by_source.get(sid, 0.0))
        sp = float(expense_by_source.get(sid, 0.0))
        source_balances.append(
            dict(source_id=sid, source_name=s["name"], income=inc, spent=sp, rest=inc - sp)
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
        source_balances=source_balances,  # можно отрисовать карточки по источникам
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
# Routes: sources (управление источниками дохода)
# -----------------------------------------------------------------------------
@app.route("/sources")
@login_required
def sources_page():
    uid = session["user_id"]
    conn = get_db()
    rows = conn.execute(
        "SELECT id, name, is_default FROM income_sources WHERE user_id=? ORDER BY is_default DESC, name",
        (uid,)
    ).fetchall()
    conn.close()
    return render_template("sources.html", sources=rows)


@app.route("/sources/add", methods=["POST"])
@login_required
def sources_add():
    uid = session["user_id"]
    name = (request.form.get("name") or "").strip()
    is_default = 1 if request.form.get("is_default") == "1" else 0
    if not name:
        flash("Введите название источника", "error")
        return redirect(url_for("sources_page"))

    conn = get_db()
    try:
        if is_default:
            conn.execute("UPDATE income_sources SET is_default=0 WHERE user_id=?", (uid,))
        conn.execute(
            "INSERT INTO income_sources(user_id, name, is_default) VALUES (?,?,?)",
            (uid, name, is_default)
        )
        conn.commit()
        flash("Источник добавлен", "success")
    except sqlite3.IntegrityError:
        flash("Источник с таким названием уже существует", "error")
    finally:
        conn.close()
    return redirect(url_for("sources_page"))


@app.route("/sources/update/<int:source_id>", methods=["POST"])
@login_required
def sources_update(source_id):
    uid = session["user_id"]
    name = (request.form.get("name") or "").strip()
    is_default = 1 if request.form.get("is_default") == "1" else 0
    if not name:
        flash("Введите название источника", "error")
        return redirect(url_for("sources_page"))
    conn = get_db()
    if is_default:
        conn.execute("UPDATE income_sources SET is_default=0 WHERE user_id=?", (uid,))
    conn.execute(
        "UPDATE income_sources SET name=?, is_default=? WHERE id=? AND user_id=?",
        (name, is_default, source_id, uid)
    )
    conn.commit()
    conn.close()
    flash("Источник обновлён", "success")
    return redirect(url_for("sources_page"))


@app.route("/sources/delete/<int:source_id>", methods=["POST"])
@login_required
def sources_delete(source_id):
    uid = session["user_id"]
    conn = get_db()
    conn.execute("DELETE FROM income_sources WHERE id=? AND user_id=?", (source_id, uid))
    conn.commit()
    conn.close()
    flash("Источник удалён", "success")
    return redirect(url_for("sources_page"))


# -----------------------------------------------------------------------------
# Routes: rules (привязки категория -> источник)
# -----------------------------------------------------------------------------
@app.route("/rules/upsert/<int:category_id>", methods=["POST"])
@login_required
def upsert_rule(category_id):
    uid = session["user_id"]
    source_id = request.form.get("source_id")
    if not source_id:
        flash("Выберите источник", "error")
        return redirect(url_for("categories"))

    conn = get_db()
    ok_src = conn.execute(
        "SELECT 1 FROM income_sources WHERE id=? AND user_id=?", (source_id, uid)
    ).fetchone()
    ok_cat = conn.execute(
        "SELECT 1 FROM categories WHERE id=? AND user_id=?", (category_id, uid)
    ).fetchone()
    if not ok_src or not ok_cat:
        conn.close()
        flash("Некорректные данные", "error")
        return redirect(url_for("categories"))

    exists = conn.execute(
        "SELECT id FROM source_category_rules WHERE user_id=? AND category_id=?",
        (uid, category_id)
    ).fetchone()
    if exists:
        conn.execute("UPDATE source_category_rules SET source_id=? WHERE id=?", (source_id, exists["id"]))
    else:
        conn.execute(
            "INSERT INTO source_category_rules(user_id, source_id, category_id) VALUES (?,?,?)",
            (uid, source_id, category_id)
        )
    conn.commit()
    conn.close()
    flash("Правило сохранено", "success")
    return redirect(url_for("categories"))


# -----------------------------------------------------------------------------
# Routes: categories / expenses / income (как раньше, но income учитывает source_id)
# -----------------------------------------------------------------------------
@app.route("/categories")
@login_required
def categories():
    uid = session["user_id"]
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM categories WHERE user_id=? ORDER BY name", (uid,)
    ).fetchall()
    # источники и действующие правила — отдадим в шаблон (если шаблон готов)
    sources = conn.execute(
        "SELECT id, name FROM income_sources WHERE user_id=? ORDER BY name", (uid,)
    ).fetchall()
    rules = conn.execute(
        "SELECT category_id, source_id FROM source_category_rules WHERE user_id=?", (uid,)
    ).fetchall()
    rules_map = {r["category_id"]: r["source_id"] for r in rules}
    conn.close()
    return render_template("categories.html", categories=rows, income_sources=sources, rules_map=rules_map)


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


@app.route("/income")
@login_required
def income_page():
    uid = session["user_id"]
    conn = get_db()
    rows = conn.execute(
        """
        SELECT id, date, amount, source_id
        FROM income_daily
        WHERE user_id = ?
        ORDER BY date DESC, id DESC
        """,
        (uid,),
    ).fetchall()
    income_sources = conn.execute(
        "SELECT id, name, is_default FROM income_sources WHERE user_id=? ORDER BY is_default DESC, name",
        (uid,)
    ).fetchall()
    conn.close()
    today = datetime.now().strftime("%Y-%m-%d")
    return render_template("income.html", incomes=rows, income_sources=income_sources, today=today)


@app.route("/income/add", methods=["POST"])
@login_required
def income_add():
    uid = session["user_id"]
    date_str = (request.form.get("date") or "").strip()
    amount_str = (request.form.get("amount") or "").strip()
    source_id = request.form.get("source_id")

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
    # если пользователь не выбрал источник — подставим дефолтный, если есть
    if not source_id:
        source_id = get_default_source_id(conn, uid)
    conn.execute(
        "INSERT INTO income_daily (user_id, date, amount, source_id) VALUES (?,?,?,?)",
        (uid, date_str, amount, source_id),
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
        "SELECT id, date, amount, source_id FROM income_daily WHERE id=? AND user_id=?",
        (income_id, uid),
    ).fetchone()
    if not row:
        conn.close()
        flash("Запись не найдена", "error")
        return redirect(url_for("income_page"))

    sources = conn.execute(
        "SELECT id, name FROM income_sources WHERE user_id=? ORDER BY name", (uid,)
    ).fetchall()

    if request.method == "POST":
        date_str = (request.form.get("date") or "").strip()
        amount_str = (request.form.get("amount") or "").strip()
        source_id = request.form.get("source_id") or None
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
            amount = float(amount_str)
            if amount <= 0:
                raise ValueError
        except Exception:
            flash("Неверные значения", "error")
            return redirect(url_for("edit_income", income_id=income_id))

        conn.execute(
            "UPDATE income_daily SET date=?, amount=?, source_id=? WHERE id=? AND user_id=?",
            (date_str, amount, source_id, income_id, uid),
        )
        conn.commit()
        conn.close()
        flash("Доход обновлён", "success")
        return redirect(url_for("income_page"))

    conn.close()
    # простой шаблон инлайн
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
            <div class="mb-3">
              <label class="form-label">Источник</label>
              <select class="form-select" name="source_id">
                <option value="">(не указан)</option>
                {% for s in sources %}
                  <option value="{{ s.id }}" {% if income.source_id == s.id %}selected{% endif %}>{{ s.name }}</option>
                {% endfor %}
              </select>
            </div>
            <div class="d-flex gap-2">
              <button class="btn btn-primary">Сохранить</button>
              <a class="btn btn-secondary" href="{{ url_for('income_page') }}">Отмена</a>
            </div>
          </form>
        </div>
        {% endblock %}
        """,
        income=row, sources=sources,
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
# Templates (минимальный набор — как раньше + страница источников)
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
    .container { max-width: 1100px; }
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
          <a class="btn btn-sm btn-outline-warning" href="{{ url_for('sources_page') }}">Источники</a>
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
    <div class="mb-3"><label class="form-label">Email</label><input class="form-control" type="email" name="email" required></div>
    <div class="mb-3"><label class="form-label">Пароль</label><input class="form-control" type="password" name="password" required></div>
    <button class="btn btn-primary w-100">Войти</button>
  </form>
  <div class="text-center mt-3"><a href="{{ url_for('register') }}">Создать аккаунт</a></div>
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
    <div class="mb-3"><label class="form-label">Имя</label><input class="form-control" name="name" required></div>
    <div class="mb-3"><label class="form-label">Email</label><input class="form-control" type="email" name="email" required></div>
    <div class="mb-3"><label class="form-label">Пароль</label><input class="form-control" type="password" name="password" required></div>
    <div class="mb-3"><label class="form-label">Повторите пароль</label><input class="form-control" type="password" name="confirm" required></div>
    <button class="btn btn-success w-100">Создать аккаунт</button>
  </form>
  <div class="text-center mt-3"><a href="{{ url_for('login') }}">У меня уже есть аккаунт</a></div>
</div>
{% endblock %}
"""

# Минимальные шаблоны, чтобы приложение запустилось.
DASHBOARD_HTML = """
{% extends "base.html" %}
{% block title %}Дашборд — CrystalBudget{% endblock %}
{% block content %}
<h3 class="mb-3">Дашборд</h3>
<p class="text-muted">Месяц: {{ current_month }}</p>

{% if source_balances and source_balances|length > 0 %}
<div class="row g-3 mb-4">
  {% for s in source_balances %}
  <div class="col-md-4">
    <div class="card">
      <div class="card-body">
        <h6 class="card-title mb-2">{{ s.source_name }}</h6>
        <div class="d-flex justify-content-between"><span>Пришло</span><strong>{{ s.income|float|round(2) }}</strong></div>
        <div class="d-flex justify-content-between"><span>Ушло</span><strong>{{ s.spent|float|round(2) }}</strong></div>
        <div class="d-flex justify-content-between"><span>Остаток</span><strong>{{ s.rest|float|round(2) }}</strong></div>
      </div>
    </div>
  </div>
  {% endfor %}
</div>
{% endif %}

<div class="card">
  <div class="card-body">
    <h6 class="card-title">Категории (лимит/факт)</h6>
    <div class="row g-2">
      {% for item in budget_data %}
      <div class="col-md-4">
        <div class="border rounded p-2">
          <div class="fw-semibold">{{ item.category_name }}</div>
          <div class="small text-muted">Лимит: {{ item.limit|float|round(2) }} • Потрачено: {{ item.spent|float|round(2) }}</div>
        </div>
      </div>
      {% endfor %}
    </div>
  </div>
</div>
{% endblock %}
"""

CATEGORIES_HTML = """
{% extends "base.html" %}
{% block title %}Категории — CrystalBudget{% endblock %}
{% block content %}
<div class="d-flex justify-content-between align-items-center mb-3">
  <h3 class="m-0">Категории</h3>
  <button class="btn btn-primary" data-bs-toggle="collapse" data-bs-target="#addCategoryForm">Добавить</button>
</div>

<div class="collapse mb-3" id="addCategoryForm">
  <div class="card card-body">
    <form method="POST" action="/categories/add">
      <div class="row g-3">
        <div class="col-md-4"><label class="form-label">Название</label><input class="form-control" name="name" required></div>
        <div class="col-md-3">
          <label class="form-label">Тип лимита</label>
          <select class="form-select" name="limit_type" required>
            <option value="fixed">Фикс</option>
            <option value="percent">Процент от дохода</option>
          </select>
        </div>
        <div class="col-md-3"><label class="form-label">Значение</label><input class="form-control" type="number" step="0.01" min="0.01" name="value" required></div>
        <div class="col-md-2 d-grid"><label class="form-label d-none d-md-block">&nbsp;</label><button class="btn btn-success">Сохранить</button></div>
      </div>
    </form>
  </div>
</div>

{% if income_sources and income_sources|length > 0 %}
<div class="alert alert-info">Для каждой категории можно выбрать источник, из которого она оплачивается.</div>
{% endif %}

<div class="table-responsive">
  <table class="table align-middle">
    <thead class="table-light">
      <tr><th>Категория</th><th>Тип/значение</th><th style="width:320px">Оплачивать из</th></tr>
    </thead>
    <tbody>
      {% for cat in categories %}
      <tr>
        <td>{{ cat.name }}</td>
        <td>{{ 'фикс' if cat.limit_type=='fixed' else 'процент' }} / {{ cat.value }}</td>
        <td>
          {% if income_sources and income_sources|length>0 %}
          <form class="d-flex gap-2" method="POST" action="{{ url_for('upsert_rule', category_id=cat.id) }}">
            <select class="form-select" name="source_id">
              {% for s in income_sources %}
                <option value="{{ s.id }}" {% if rules_map.get(cat.id)==s.id %}selected{% endif %}>{{ s.name }}</option>
              {% endfor %}
            </select>
            <button class="btn btn-outline-primary">Сохранить</button>
          </form>
          {% else %}
          <em class="text-muted">Добавьте источники на странице «Источники»</em>
          {% endif %}
        </td>
      </tr>
      {% endfor %}
    </tbody>
  </table>
</div>
{% endblock %}
"""

EXPENSES_HTML = """
{% extends "base.html" %}
{% block title %}Расходы — CrystalBudget{% endblock %}
{% block content %}
<div class="d-flex justify-content-between align-items-center mb-3">
  <h3 class="m-0">Расходы</h3>
  <button class="btn btn-primary" data-bs-toggle="collapse" data-bs-target="#addExpenseForm">Добавить</button>
</div>

<div class="collapse mb-3" id="addExpenseForm">
  <div class="card card-body">
    <form method="POST" action="/expenses">
      <div class="row g-3">
        <div class="col-md-3"><label class="form-label">Дата</label><input type="date" name="date" value="{{ today }}" class="form-control" required></div>
        <div class="col-md-3">
          <label class="form-label">Категория</label>
          <select name="category_id" class="form-select" required>
            <option value="">Выберите категорию</option>
            {% for cat in categories %}<option value="{{ cat.id }}">{{ cat.name }}</option>{% endfor %}
          </select>
        </div>
        <div class="col-md-2"><label class="form-label">Сумма</label><input type="number" step="0.01" min="0.01" name="amount" class="form-control" required></div>
        <div class="col-md-3"><label class="form-label">Комментарий</label><input type="text" name="note" class="form-control"></div>
        <div class="col-md-1 d-grid"><label class="form-label d-none d-md-block">&nbsp;</label><button class="btn btn-success">Добавить</button></div>
      </div>
    </form>
  </div>
</div>

<div class="table-responsive">
  <table class="table table-striped align-middle">
    <thead class="table-light"><tr><th>Дата</th><th>Категория</th><th class="text-end">Сумма</th><th>Комментарий</th><th class="text-end">Действия</th></tr></thead>
    <tbody>
      {% for e in expenses %}
      <tr>
        <td>{{ e.date|format_date_with_day }}</td>
        <td>{{ e.category_name }}</td>
        <td class="text-end fw-semibold">{{ e.amount|format_amount }} ₽</td>
        <td>{{ e.note or '' }}</td>
        <td class="text-end">
          <form method="POST" action="{{ url_for('delete_expense', expense_id=e.id) }}" class="d-inline">
            <button class="btn btn-sm btn-outline-danger" onclick="return confirm('Удалить расход?\\nДата: {{ e.date|format_date_with_day }}\\nКатегория: {{ e.category_name }}\\nСумма: {{ e.amount|format_amount }} ₽')">Удалить</button>
          </form>
        </td>
      </tr>
      {% endfor %}
    </tbody>
  </table>
</div>
{% endblock %}
"""

INCOME_HTML = """
{% extends "base.html" %}
{% block title %}Доходы — CrystalBudget{% endblock %}
{% block content %}
<div class="d-flex justify-content-between align-items-center mb-3">
  <h3 class="m-0">Доходы</h3>
</div>

<div class="card card-body mb-3">
  <form method="POST" action="{{ url_for('income_add') }}">
    <div class="row g-3">
      <div class="col-md-3"><label class="form-label">Дата</label><input type="date" id="date" name="date" value="{{ today }}" class="form-control" required></div>
      <div class="col-md-3"><label class="form-label">Сумма</label><input type="number" id="amount" name="amount" step="0.01" min="0.01" class="form-control" required></div>
      <div class="col-md-4">
        <label class="form-label">Источник</label>
        <select class="form-select" name="source_id">
          <option value="">(не указан)</option>
          {% for s in income_sources %}
            <option value="{{ s.id }}" {% if s.is_default %}selected{% endif %}>{{ s.name }}</option>
          {% endfor %}
        </select>
      </div>
      <div class="col-md-2 d-grid"><label class="form-label d-none d-md-block">&nbsp;</label><button class="btn btn-success">Добавить</button></div>
    </div>
  </form>
</div>

<div class="table-responsive">
  <table class="table table-striped align-middle">
    <thead class="table-light"><tr><th>Дата</th><th class="text-end">Сумма</th><th>Источник</th><th class="text-end">Действия</th></tr></thead>
    <tbody>
      {% for i in incomes %}
      <tr>
        <td>{{ i.date|format_date_with_day }}</td>
        <td class="text-end fw-semibold">{{ i.amount|format_amount }} ₽</td>
        <td>
          {% if i.source_id %}
            {% set nm = (income_sources | selectattr('id','equalto', i.source_id) | list) %}
            {{ nm[0].name if nm and nm[0] else '—' }}
          {% else %}—{% endif %}
        </td>
        <td class="text-end">
          <a class="btn btn-sm btn-outline-primary" href="{{ url_for('edit_income', income_id=i.id) }}">Изм.</a>
          <form class="d-inline" method="POST" action="{{ url_for('delete_income', income_id=i.id) }}"><button class="btn btn-sm btn-outline-danger" onclick="return confirm('Удалить доход?')">Удалить</button></form>
        </td>
      </tr>
      {% endfor %}
    </tbody>
  </table>
</div>
{% endblock %}
{% block scripts %}
<script>
document.addEventListener('DOMContentLoaded', function(){
  const dateInput = document.getElementById('date');
  if (dateInput && !dateInput.value) {
    const now = new Date();
    dateInput.value = now.toISOString().slice(0, 10);
  }
});
</script>
{% endblock %}
"""

SOURCES_HTML = """
{% extends "base.html" %}
{% block title %}Источники — CrystalBudget{% endblock %}
{% block content %}
<div class="d-flex justify-content-between align-items-center mb-3">
  <h3 class="m-0">Источники доходов</h3>
</div>

<div class="card card-body mb-3">
  <form method="POST" action="{{ url_for('sources_add') }}">
    <div class="row g-3">
      <div class="col-md-6"><label class="form-label">Название</label><input class="form-control" name="name" placeholder="ЗП, Аванс, Декретные" required></div>
      <div class="col-md-4"><label class="form-label">По умолчанию</label><select class="form-select" name="is_default"><option value="0">Нет</option><option value="1">Да</option></select></div>
      <div class="col-md-2 d-grid"><label class="form-label d-none d-md-block">&nbsp;</label><button class="btn btn-success">Добавить</button></div>
    </div>
  </form>
</div>

<div class="table-responsive">
  <table class="table align-middle">
    <thead class="table-light"><tr><th>Название</th><th>По умолчанию</th><th class="text-end">Действия</th></tr></thead>
    <tbody>
      {% for s in sources %}
      <tr>
        <td>{{ s.name }}</td>
        <td>{{ 'Да' if s.is_default else 'Нет' }}</td>
        <td class="text-end">
          <form class="d-inline" method="POST" action="{{ url_for('sources_update', source_id=s.id) }}">
            <input type="hidden" name="name" value="{{ s.name }}">
            <input type="hidden" name="is_default" value="{{ 1 if not s.is_default else 0 }}">
            <button class="btn btn-sm btn-outline-primary">{{ 'Сделать дефолтным' if not s.is_default else 'Убрать дефолт' }}</button>
          </form>
          <form class="d-inline" method="POST" action="{{ url_for('sources_delete', source_id=s.id) }}">
            <button class="btn btn-sm btn-outline-danger" onclick="return confirm('Удалить источник?')">Удалить</button>
          </form>
        </td>
      </tr>
      {% endfor %}
    </tbody>
  </table>
</div>
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
                "sources.html": SOURCES_HTML,
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
    ensure_income_sources_tables()
    migrate_income_to_daily_if_needed()
    add_source_id_column_if_missing()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)