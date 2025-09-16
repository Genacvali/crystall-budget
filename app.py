import os
import sqlite3
import logging
import requests 
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from functools import wraps
from logging.handlers import RotatingFileHandler

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

# Стабильный секретный ключ (вынесен в переменную окружения)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-only-insecure-key-change-in-production')
if app.config['SECRET_KEY'] == 'dev-only-insecure-key-change-in-production':
    print("WARNING: Using insecure default secret key. Set SECRET_KEY environment variable for production!")

# Долгая "постоянная" сессия (30 дней)
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)

# Атрибуты куки для безопасности и PWA
https_mode = os.environ.get('HTTPS_MODE', 'False').lower() == 'true'

# Основные настройки безопасности кук
app.config['SESSION_COOKIE_SECURE'] = https_mode  # HTTPS только для prod
app.config['SESSION_COOKIE_HTTPONLY'] = True  # Защита от XSS
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # CSRF защита

# Дополнительные настройки безопасности
if https_mode:
    # В продакшене добавляем дополнительную защиту
    app.config['SESSION_COOKIE_NAME'] = 'cb_session'  # Скрываем Flask
    app.config['WTF_CSRF_TIME_LIMIT'] = 3600  # CSRF токен на 1 час
else:
    # В разработке используем стандартные настройки
    app.config['SESSION_COOKIE_NAME'] = 'session'

# Если нужны поддомены, раскомментируй:
# app.config['SESSION_COOKIE_DOMAIN'] = '.yourdomain.com'

DB_PATH = os.environ.get("BUDGET_DB", "budget.db")

# Uploads (аватары)
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024  # 2 MB
AVATAR_DIR = os.path.join(os.path.dirname(__file__), 'static', 'avatars')
os.makedirs(AVATAR_DIR, exist_ok=True)

ALLOWED_AVATAR_EXT = {'.png', '.jpg', '.jpeg', '.webp'}

def _allowed_avatar(filename: str) -> bool:
    _, ext = os.path.splitext(filename.lower())
    return ext in ALLOWED_AVATAR_EXT

# -----------------------------------------------------------------------------
# Logging setup
# -----------------------------------------------------------------------------
def setup_logging():
    # Создаем папку для логов если её нет
    log_dir = os.path.join(os.path.dirname(__file__), 'logs')
    os.makedirs(log_dir, exist_ok=True)
    
    # Настройка ротации логов (максимум 10MB на файл, 5 файлов)
    log_file = os.path.join(log_dir, 'crystalbudget.log')
    file_handler = RotatingFileHandler(
        log_file, 
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    
    # Формат логов
    formatter = logging.Formatter(
        '%(asctime)s %(levelname)s [%(name)s] %(message)s'
    )
    file_handler.setFormatter(formatter)
    
    # Настройка уровня логирования
    log_level = os.environ.get('LOG_LEVEL', 'INFO').upper()
    file_handler.setLevel(getattr(logging, log_level))
    
    # Добавляем обработчик к Flask приложению
    app.logger.addHandler(file_handler)
    app.logger.setLevel(getattr(logging, log_level))
    
    # Логирование Werkzeug (встроенный сервер Flask)
    werkzeug_logger = logging.getLogger('werkzeug')
    werkzeug_logger.addHandler(file_handler)
    werkzeug_logger.setLevel(logging.INFO)
    
    app.logger.info('Logging system initialized')
    app.logger.info(f'Log level: {log_level}')
    app.logger.info(f'Log file: {log_file}')

# Инициализируем логирование
setup_logging()

# Валюты
CURRENCIES = {
    "RUB": {"symbol": "₽", "label": "Рубль"},
    "USD": {"symbol": "$", "label": "Доллар"},
    "EUR": {"symbol": "€", "label": "Евро"},
    "AMD": {"symbol": "֏", "label": "Драм"},
    "GEL": {"symbol": "₾", "label": "Лари"},
}
DEFAULT_CURRENCY = "RUB"
# Кэш курсов валют
EXR_CACHE_TTL_SECONDS = int(os.environ.get("EXR_CACHE_TTL_SECONDS", str(12 * 3600)))  # 12 часов
EXR_BRIDGE = os.environ.get("EXR_BRIDGE", "USD").upper()  # промежуточная валюта для кросс-курса
@app.context_processor
def inject_currency():
    code = session.get("currency", DEFAULT_CURRENCY)
    info = CURRENCIES.get(code, CURRENCIES[DEFAULT_CURRENCY])
    return dict(currency_code=code, currency_symbol=info["symbol"], currencies=CURRENCIES)

# -----------------------------------------------------------------------------
# Currency conversion helper
# -----------------------------------------------------------------------------
BRIDGE_CURRENCY = EXR_BRIDGE
# TTL берём из верхнего EXR_CACHE_TTL_SECONDS (ничего не переопределяем)

def _norm_cur(curr):
    """Нормализует валюту к верхнему регистру."""
    return str(curr).strip().upper()

def _db_conn():
    """Простой контекст-менеджер для БД."""
    conn = get_db()
    try:
        yield conn
    finally:
        conn.close()

def _fetch_rate_exchangerate_host(frm: str, to: str) -> float:
    """Прямой запрос к exchangerate.host"""
    import requests
    url = "https://api.exchangerate.host/convert"
    r = requests.get(url, params={"from": frm, "to": to}, timeout=6)
    r.raise_for_status()
    data = r.json()
    if not data or "result" not in data or not data["result"]:
        raise ValueError("no result from exchangerate.host")
    return float(data["result"])

def _fetch_rate_exchangerate_host_base(base: str, sym: str) -> float:
    """Получить курс base -> sym одной пачкой"""
    import requests
    url = "https://api.exchangerate.host/latest"
    r = requests.get(url, params={"base": base, "symbols": sym}, timeout=6)
    r.raise_for_status()
    data = r.json()
    rate = data.get("rates", {}).get(sym)
    if not rate:
        raise ValueError("no rate for symbol in latest")
    return float(rate)

def get_exchange_rate_via_bridge(frm: str, to: str, bridge: str = BRIDGE_CURRENCY) -> float:
    """Кросс-курс через промежуточную валюту (по умолчанию USD)."""
    frm, to, bridge = _norm_cur(frm), _norm_cur(to), _norm_cur(bridge)
    if frm == to:
        return 1.0
    if frm == bridge:
        # bridge -> to
        return _fetch_rate_exchangerate_host_base(bridge, to)
    if to == bridge:
        # frm -> bridge
        return _fetch_rate_exchangerate_host_base(frm, bridge)
    # frm -> bridge * bridge -> to
    r1 = _fetch_rate_exchangerate_host_base(frm, bridge)
    r2 = _fetch_rate_exchangerate_host_base(bridge, to)
    return float(r1) * float(r2)

def get_exchange_rate(frm: str, to: str) -> float:
    """
    1) читаем кэш из exchange_rates (TTL);
    2) пробуем прямую пару через exchangerate.host;
    3) пробуем кросс-курс через USD (или EXR_BRIDGE);
    4) сохраняем в кэш; если всё сломалось — отдаём старый кэш, если он был.
    """
    from datetime import datetime, timedelta
    
    frm, to = _norm_cur(frm), _norm_cur(to)
    if frm == to:
        return 1.0

    now = datetime.utcnow()
    conn = get_db()
    try:
        conn.execute("PRAGMA foreign_keys=ON")
        row = conn.execute(
            "SELECT rate, updated_at FROM exchange_rates WHERE from_currency=? AND to_currency=?",
            (frm, to)
        ).fetchone()
        
        if row:
            try:
                updated = datetime.fromisoformat(row["updated_at"].replace("Z",""))
            except Exception:
                updated = now - timedelta(days=365)
            if (now - updated).total_seconds() < EXR_CACHE_TTL_SECONDS and row["rate"] and row["rate"] > 0:
                return float(row["rate"])

        # 2) прямая пара
        try:
            rate = _fetch_rate_exchangerate_host(frm, to)
        except Exception:
            rate = None

        # 3) через мост (USD по умолчанию)
        if not rate:
            try:
                rate = get_exchange_rate_via_bridge(frm, to, BRIDGE_CURRENCY)
            except Exception:
                rate = None

        if rate and rate > 0:
            conn.execute(
                """
                INSERT INTO exchange_rates(from_currency, to_currency, rate, updated_at)
                VALUES(?,?,?,?)
                ON CONFLICT(from_currency, to_currency) DO UPDATE SET
                  rate=excluded.rate,
                  updated_at=excluded.updated_at
                """,
                (frm, to, float(rate), now.isoformat(timespec="seconds")+"Z"),
            )
            conn.commit()
            return float(rate)

        # 4) fallback: старый кэш, если был
        if row and row["rate"]:
            return float(row["rate"])

        raise RuntimeError(f"cannot fetch exchange rate {frm}->{to}")
        
    except Exception as e:
        app.logger.error(f"Exchange rate error {frm}->{to}: {e}")
        return 1.0  # Fallback
    finally:
        conn.close()

def convert_currency(amount, from_currency, to_currency):
    """Конвертирует сумму из одной валюты в другую."""
    if from_currency == to_currency:
        return amount
    
    try:
        rate = get_exchange_rate(from_currency, to_currency)
        return float(amount) * rate
    except Exception as e:
        app.logger.error(f"Currency conversion error: {e}")
        return amount

# -----------------------------------------------------------------------------
# Jinja filters
# -----------------------------------------------------------------------------
@app.template_filter("format_amount")
def format_amount(value, from_currency=None):
    """Число с пробелами для тысяч, автоматическая конвертация валют."""
    try:
        # Автоматическая конвертация если указана исходная валюта
        if from_currency and 'currency' in session:
            target_currency = session['currency']
            if from_currency != target_currency:
                value = convert_currency(value, from_currency, target_currency)
        
        d = Decimal(str(value))
    except Exception:
        return str(value)
    # округлим до 2 знаков – но целые покажем без дробной части
    q = d.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    s = f"{q:,.2f}".replace(",", " ")
    return s[:-3] if s.endswith("00") else s

@app.template_filter("format_percent")
def format_percent(value):
    """Проценты без лишних хвостов, максимум 2 знака после точки."""
    try:
        v = float(value)
        # целые без .0, иначе до 2 знаков
        return f"{int(v)}" if abs(v - int(v)) < 1e-9 else f"{v:.2f}".rstrip('0').rstrip('.')
    except:
        return str(value)

@app.template_filter("format_date_with_day")
def format_date_with_day(value):
    try:
        dt = datetime.strptime(value, "%Y-%m-%d")
        return dt.strftime("%d.%m.%Y")
    except Exception:
        return value

# -----------------------------------------------------------------------------
# Validation helpers
# -----------------------------------------------------------------------------
def validate_amount(amount_str):
    """Validate and return amount as float, or None if invalid."""
    if not amount_str or not amount_str.strip():
        return None
    try:
        amount = float(amount_str.strip())
        return amount if amount > 0 else None
    except (ValueError, TypeError):
        return None

def validate_date(date_str):
    """Validate and return date string in YYYY-MM-DD format, or None if invalid."""
    if not date_str or not date_str.strip():
        return None
    try:
        datetime.strptime(date_str.strip(), "%Y-%m-%d")
        return date_str.strip()
    except ValueError:
        return None

def sanitize_string(s, max_length=255):
    """Sanitize and limit string length."""
    if not s:
        return ""
    return str(s).strip()[:max_length]

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

        -- Performance indexes
        CREATE INDEX IF NOT EXISTS idx_expenses_user_date ON expenses(user_id, date DESC);
        CREATE INDEX IF NOT EXISTS idx_expenses_user_month ON expenses(user_id, month);
        CREATE INDEX IF NOT EXISTS idx_expenses_category ON expenses(category_id);
        CREATE INDEX IF NOT EXISTS idx_categories_user ON categories(user_id);
        CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
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

        -- Income indexes
        CREATE INDEX IF NOT EXISTS idx_income_daily_user_date ON income_daily(user_id, date DESC);
        CREATE INDEX IF NOT EXISTS idx_income_daily_source ON income_daily(source_id);
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


def add_category_type_column_if_missing():
    """Добавляет колонку category_type в categories, если её нет."""
    conn = get_db()
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(categories)")
    cols = [r[1] for r in cur.fetchall()]
    if "category_type" not in cols:
        try:
            cur.execute("ALTER TABLE categories ADD COLUMN category_type TEXT DEFAULT 'expense' CHECK(category_type IN ('expense','income'))")
            conn.commit()
            print("Added category_type column to categories table")
        except sqlite3.OperationalError as e:
            print(f"Failed to add category_type column: {e}")
    conn.close()


def add_currency_columns_if_missing():
    """Добавляет колонки currency в expenses и income_daily, если их нет."""
    conn = get_db()
    cur = conn.cursor()
    
    # Проверяем expenses
    try:
        cur.execute("ALTER TABLE expenses ADD COLUMN currency TEXT DEFAULT 'RUB'")
        print("Added currency column to expenses table")
    except Exception:
        pass  # Колонка уже существует или ошибка
    
    # Проверяем income_daily
    try:
        cur.execute("ALTER TABLE income_daily ADD COLUMN currency TEXT DEFAULT 'RUB'")
        print("Added currency column to income_daily table")
    except Exception:
        pass  # Колонка уже существует или ошибка
    
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


# Делаем все сессии permanent по умолчанию
@app.before_request
def make_session_permanent():
    session.permanent = True

# Обработка плохих запросов
@app.before_request
def validate_request():
    # Логируем все POST запросы для отладки
    if request.method == 'POST':
        app.logger.info(f'POST request to {request.endpoint} from {request.remote_addr}')
        app.logger.debug(f'Content-Type: {request.content_type}')
        app.logger.debug(f'Form keys: {list(request.form.keys())}')
    
    # Проверяем Content-Type для POST запросов к формам
    if request.method == 'POST' and request.endpoint in ['register', 'login']:
        content_type = request.content_type or ''
        if not content_type.startswith('application/x-www-form-urlencoded') and \
           not content_type.startswith('multipart/form-data'):
            app.logger.warning(f'Invalid Content-Type for form: {content_type} from {request.remote_addr}')
            # Не блокируем, но логируем

# -----------------------------------------------------------------------------
# Routes: favicon and static files
# -----------------------------------------------------------------------------
@app.route('/favicon.ico')
def favicon():
    return redirect(url_for('static', filename='icons/icon-192.png'))

@app.route('/logs')
@login_required  
def view_logs():
    try:
        log_file = os.path.join(os.path.dirname(__file__), 'logs', 'crystalbudget.log')
        if os.path.exists(log_file):
            with open(log_file, 'r', encoding='utf-8') as f:
                # Читаем последние 100 строк
                lines = f.readlines()[-100:]
            log_content = ''.join(lines)
        else:
            log_content = 'Лог файл не найден'
        
        return render_template_string('''
        <!DOCTYPE html>
        <html lang="ru">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Логи - CrystalBudget</title>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
            <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.css" rel="stylesheet">
            <style>
                .log-content {
                    background-color: #1a1a1a;
                    color: #00ff00;
                    font-family: 'Courier New', monospace;
                    font-size: 12px;
                    padding: 20px;
                    border-radius: 8px;
                    max-height: 70vh;
                    overflow-y: auto;
                    white-space: pre-wrap;
                    word-break: break-word;
                }
            </style>
        </head>
        <body>
            <div class="container mt-4">
                <div class="d-flex justify-content-between align-items-center mb-3">
                    <h2>💎 Логи приложения</h2>
                    <div>
                        <a href="{{ url_for('dashboard') }}" class="btn btn-primary">← Назад</a>
                        <a href="{{ url_for('view_logs') }}" class="btn btn-success">🔄 Обновить</a>
                    </div>
                </div>
                <div class="alert alert-info">
                    <i class="bi bi-info-circle"></i> 
                    Показаны последние 100 строк из файла: logs/crystalbudget.log
                </div>
                <div class="log-content">{{ log_content }}</div>
            </div>
        </body>
        </html>
        ''', log_content=log_content)
    except Exception as e:
        app.logger.error(f'Error reading logs: {e}')
        return f'Ошибка чтения логов: {e}'

# Error handlers
@app.errorhandler(400)
def bad_request(error):
    app.logger.error(f'400 Bad Request: {request.url} - {request.remote_addr}')
    return render_template_string('''
    <div style="text-align: center; padding: 2rem; font-family: Arial, sans-serif;">
        <h2>🚫 Плохой запрос</h2>
        <p>Браузер отправил запрос, который сервер не смог понять.</p>
        <a href="{{ url_for('dashboard') }}" style="color: #0d6efd;">← Вернуться на главную</a>
    </div>
    '''), 400

@app.errorhandler(404)
def page_not_found(error):
    app.logger.warning(f'404 Not Found: {request.url} - {request.remote_addr}')
    return render_template_string('''
    <div style="text-align: center; padding: 2rem; font-family: Arial, sans-serif;">
        <h2>💎 Страница не найдена</h2>
        <p>Запрашиваемая страница не существует.</p>
        <a href="{{ url_for('dashboard') }}" style="color: #0d6efd;">← Вернуться на главную</a>
    </div>
    '''), 404

@app.errorhandler(500)
def internal_error(error):
    app.logger.error(f'500 Internal Server Error: {request.url} - {error}')
    return render_template_string('''
    <div style="text-align: center; padding: 2rem; font-family: Arial, sans-serif;">
        <h2>💥 Внутренняя ошибка сервера</h2>
        <p>Произошла ошибка на сервере. Попробуйте позже.</p>
        <a href="{{ url_for('dashboard') }}" style="color: #0d6efd;">← Вернуться на главную</a>
    </div>
    '''), 500

# -----------------------------------------------------------------------------
# Routes: currency switcher
# -----------------------------------------------------------------------------
@app.route("/set-currency", methods=["POST"])
@login_required
def set_currency():
    payload = request.get_json(silent=True) or {}
    code = (request.form.get("currency") or payload.get("currency") or "").upper()
    if code in CURRENCIES:
        session["currency"] = code
        if request.is_json:
            return {"success": True, "currency": code, "symbol": CURRENCIES[code]["symbol"]}
        flash("Валюта обновлена", "success")
    else:
        if request.is_json:
            return {"success": False, "error": "Неизвестная валюта"}, 400
        flash("Неизвестная валюта", "error")
    return redirect(request.referrer or url_for("dashboard"))


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
        try:
            email = request.form.get("email", "").lower().strip()
            name = request.form.get("name", "").strip()
            password = request.form.get("password", "")
            
            app.logger.info(f'Registration attempt for email: {email}, name: {name}')

            # Валидация на сервере
            if not email or not name or not password:
                app.logger.warning(f'Registration failed - missing fields for email: {email}')
                flash("Все поля обязательны для заполнения", "error")
                return render_template("register.html")
            
            if len(password) < 6:
                app.logger.warning(f'Registration failed - password too short for email: {email}')
                flash("Пароль должен содержать минимум 6 символов", "error")
                return render_template("register.html")
            
            if ' ' in password:
                app.logger.warning(f'Registration failed - password contains spaces for email: {email}')
                flash("Пароль не должен содержать пробелы", "error")
                return render_template("register.html")
                
        except Exception as e:
            app.logger.error(f'Registration form parsing error: {e} - {request.remote_addr}')
            flash("Ошибка обработки формы. Попробуйте еще раз", "error")
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
            
            if not user:
                raise Exception("Failed to retrieve user after insertion")
                
            app.logger.info(f'Successful registration for user: {email} (ID: {user["id"]})')
            
            session["user_id"] = user["id"]
            session["email"] = email
            session["name"] = name
            conn.close()
            return redirect(url_for("dashboard"))
            
        except sqlite3.IntegrityError as e:
            app.logger.warning(f'Registration failed - email already exists: {email} - {e}')
            flash("Email уже зарегистрирован", "error")
            conn.close()
            return render_template("register.html")
        except Exception as e:
            app.logger.error(f'Database error during registration for {email}: {e}')
            flash("Ошибка сервера. Попробуйте позже", "error")
            conn.close()
            return render_template("register.html")

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"].lower().strip()
        password = request.form["password"]
        
        app.logger.info(f'Login attempt for email: {email}')

        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        conn.close()
        if user and check_password_hash(user["password_hash"], password):
            session["user_id"] = user["id"]
            session["email"] = user["email"]
            session["name"] = user["name"]
            # Загружаем настройки пользователя
            # Безопасный доступ к колонкам (могут отсутствовать в старой схеме)
            try:
                session["theme"] = user["theme"] if user["theme"] else "light"
            except (KeyError, IndexError):
                session["theme"] = "light"

            try:
                session["currency"] = user["currency"] if user["currency"] else "RUB"
            except (KeyError, IndexError):
                session["currency"] = "RUB"
            app.logger.info(f'Successful login for user: {email} (ID: {user["id"]})')
            return redirect(url_for("dashboard"))
        
        app.logger.warning(f'Failed login attempt for email: {email}')
        flash("Неверный email или пароль", "error")

    return render_template("login.html")


@app.route("/logout")
def logout():
    user_email = session.get("email", "unknown")
    app.logger.info(f'User logout: {user_email}')
    session.clear()
    return redirect(url_for("login"))


# -----------------------------------------------------------------------------
# Routes: account (личный кабинет)
# -----------------------------------------------------------------------------
from werkzeug.utils import secure_filename

@app.route("/account", methods=["GET", "POST"])
@login_required
def account():
    uid = session["user_id"]
    conn = get_db()
    
    # Безопасное получение данных пользователя
    try:
        user = conn.execute(
            "SELECT id, email, name, timezone, locale, default_currency, theme, avatar_path FROM users WHERE id=?",
            (uid,)
        ).fetchone()
    except sqlite3.OperationalError:
        # Если новые поля не существуют, используем базовую версию
        user = conn.execute("SELECT id, email, name FROM users WHERE id=?", (uid,)).fetchone()
        if user:
            # Создаем словарь с дефолтными значениями
            user_data = {
                'id': user['id'],
                'email': user['email'], 
                'name': user['name'],
                'timezone': 'UTC',
                'locale': 'ru',
                'default_currency': 'RUB', 
                'theme': 'light',
                'avatar_path': None
            }
            # Простой объект для совместимости с шаблоном
            user = type('User', (), user_data)()

    if request.method == "POST":
        # Обновление базовых полей (имя и email всегда есть)
        name = sanitize_string(request.form.get("name"), 120)
        email = (request.form.get("email") or "").strip().lower()

        # Проверим уникальность email, если поменяли
        if email and email != user.email:
            exists = conn.execute("SELECT 1 FROM users WHERE email=? AND id<>?", (email, uid)).fetchone()
            if exists:
                flash("Этот email уже занят", "error")
                conn.close()
                return redirect(url_for("account"))

        # Пробуем обновить с расширенными полями
        try:
            timezone = sanitize_string(request.form.get("timezone"), 64) or "UTC"
            locale = sanitize_string(request.form.get("locale"), 8) or "ru" 
            default_currency = (request.form.get("default_currency") or "RUB").upper()
            theme = request.form.get("theme") or "light"
            
            conn.execute("""
                UPDATE users
                SET name=?, email=?, timezone=?, locale=?, default_currency=?, theme=?
                WHERE id=?
            """, (name or user.name, email or user.email, timezone, locale, default_currency, theme, uid))
        except sqlite3.OperationalError:
            # Если расширенные поля не существуют, обновляем только базовые
            conn.execute("UPDATE users SET name=?, email=? WHERE id=?", 
                        (name or user.name, email or user.email, uid))
        
        conn.commit()
        session["email"] = email or user.email
        session["name"] = name or user.name
        flash("Настройки сохранены", "success")
        conn.close()
        return redirect(url_for("account"))

    conn.close()
    return render_template("account.html", user=user, currencies=CURRENCIES)

@app.route("/account/password", methods=["POST"])
@login_required
def account_password():
    uid = session["user_id"]
    old = request.form.get("old_password") or ""
    new = request.form.get("new_password") or ""
    confirm = request.form.get("confirm_password") or ""

    if len(new) < 6:
        flash("Новый пароль слишком короткий (мин. 6 символов)", "error")
        return redirect(url_for("account"))
    if new != confirm:
        flash("Пароли не совпадают", "error")
        return redirect(url_for("account"))

    conn = get_db()
    user = conn.execute("SELECT password_hash FROM users WHERE id=?", (uid,)).fetchone()
    if not user or not check_password_hash(user["password_hash"], old):
        conn.close()
        flash("Текущий пароль неверный", "error")
        return redirect(url_for("account"))

    conn.execute("UPDATE users SET password_hash=? WHERE id=?", (generate_password_hash(new), uid))
    conn.commit()
    conn.close()
    flash("Пароль обновлён", "success")
    return redirect(url_for("account"))

@app.route("/account/avatar", methods=["POST"])
@login_required
def account_avatar():
    uid = session["user_id"]
    file = request.files.get("avatar")
    if not file or not file.filename:
        flash("Файл не выбран", "error")
        return redirect(url_for("account"))

    if not _allowed_avatar(file.filename):
        flash("Разрешены PNG/JPG/JPEG/WEBP", "error")
        return redirect(url_for("account"))

    filename = secure_filename(file.filename)
    _, ext = os.path.splitext(filename.lower())
    # персонализированное имя — userID + timestamp
    new_name = f"user_{uid}_{int(datetime.utcnow().timestamp())}{ext}"
    save_path = os.path.join(AVATAR_DIR, new_name)
    file.save(save_path)

    rel_path = f"avatars/{new_name}"  # для url_for('static', filename=rel_path)
    conn = get_db()
    try:
        conn.execute("UPDATE users SET avatar_path=? WHERE id=?", (rel_path, uid))
        conn.commit()
        flash("Аватар обновлён", "success")
    except sqlite3.OperationalError as e:
        if "no such column: avatar_path" in str(e):
            flash("Функция аватаров временно недоступна. Обратитесь к администратору.", "warning")
            # Remove the uploaded file since we can't save the path
            try:
                os.remove(save_path)
            except OSError:
                pass
        else:
            flash("Ошибка обновления аватара", "error")
    finally:
        conn.close()

    return redirect(url_for("account"))

@app.route("/account/profile", methods=["POST"])
@login_required
def update_profile():
    """Обновление основной информации профиля"""
    uid = session["user_id"]
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip().lower()
    
    if not name:
        flash("Имя не может быть пустым", "error")
        return redirect(url_for("account"))
    
    if not email:
        flash("Email не может быть пустым", "error")
        return redirect(url_for("account"))
    
    # Простая валидация email
    if "@" not in email or "." not in email:
        flash("Некорректный формат email", "error")
        return redirect(url_for("account"))
    
    conn = get_db()
    try:
        # Проверяем, не занят ли email другим пользователем
        existing = conn.execute(
            "SELECT id FROM users WHERE email = ? AND id != ?", 
            (email, uid)
        ).fetchone()
        
        if existing:
            flash("Этот email уже используется другим пользователем", "error")
            return redirect(url_for("account"))
        
        # Обновляем профиль
        conn.execute(
            "UPDATE users SET name = ?, email = ? WHERE id = ?",
            (name, email, uid)
        )
        conn.commit()
        flash("Профиль обновлен", "success")
        
    except sqlite3.Error as e:
        flash("Ошибка обновления профиля", "error")
        app.logger.error(f"Profile update error for user {uid}: {e}")
    finally:
        conn.close()
    
    return redirect(url_for("account"))


# -----------------------------------------------------------------------------
# Routes: dashboard
# -----------------------------------------------------------------------------
@app.route("/dashboard")
@login_required
def dashboard():
    month = request.args.get("month") or datetime.now().strftime("%Y-%m")
    conn = get_db()
    uid = session["user_id"]
    
    # Подготовка данных для навигации по месяцам
    try:
        current_date = datetime.strptime(month, "%Y-%m")
        prev_month = (current_date.replace(day=1) - timedelta(days=1)).strftime("%Y-%m")
        next_month = (current_date.replace(day=28) + timedelta(days=4)).replace(day=1).strftime("%Y-%m")
        current_month_name = current_date.strftime("%B %Y")
        
        # Переводим название месяца на русский
        month_names_ru = {
            "January": "Январь", "February": "Февраль", "March": "Март", "April": "Апрель",
            "May": "Май", "June": "Июнь", "July": "Июль", "August": "Август",
            "September": "Сентябрь", "October": "Октябрь", "November": "Ноябрь", "December": "Декабрь"
        }
        
        eng_month_name = current_date.strftime("%B")
        current_month_name = f"{month_names_ru.get(eng_month_name, eng_month_name)} {current_date.year}"
        
        month_names = ["Январь", "Февраль", "Март", "Апрель", "Май", "Июнь", 
                       "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"]
    except ValueError:
        # Если формат месяца некорректный, используем текущий
        month = datetime.now().strftime("%Y-%m")
        current_date = datetime.now()
        prev_month = (current_date.replace(day=1) - timedelta(days=1)).strftime("%Y-%m")
        next_month = (current_date.replace(day=28) + timedelta(days=4)).replace(day=1).strftime("%Y-%m")
        current_month_name = "Текущий месяц"
        month_names = ["Январь", "Февраль", "Март", "Апрель", "Май", "Июнь", 
                       "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"]

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

    # правило категория->источник (нужно раньше для расчета лимитов)
    rule_rows = conn.execute(
        "SELECT category_id, source_id FROM source_category_rules WHERE user_id=?",
        (uid,),
    ).fetchall()
    rule_map = {r["category_id"]: r["source_id"] for r in rule_rows}
    
    # приход по источникам (нужно раньше для расчета процентных лимитов)
    sources = conn.execute(
        "SELECT id, name FROM income_sources WHERE user_id=? ORDER BY name", (uid,)
    ).fetchall()
    
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

    # расчёт лимитов категорий с учётом процента от дохода и многоисточниковости
    limits = conn.execute(
        "SELECT id, name, limit_type, value, multi_source FROM categories WHERE user_id=?",
        (uid,),
    ).fetchall()

    # Получаем связи категорий с источниками для многоисточниковых категорий
    multi_source_links = {}
    multi_source_rows = conn.execute("""
        SELECT category_id, source_id, percentage, 
               (SELECT name FROM income_sources WHERE id = cis.source_id) as source_name
        FROM category_income_sources cis
        WHERE user_id = ?
        ORDER BY category_id, source_id
    """, (uid,)).fetchall()
    
    for link in multi_source_rows:
        cat_id = link['category_id']
        if cat_id not in multi_source_links:
            multi_source_links[cat_id] = []
        multi_source_links[cat_id].append({
            'source_id': link['source_id'],
            'source_name': link['source_name'],
            'percentage': float(link['percentage'])
        })

    data = []
    for row in limits:
        cat_id = row["id"]
        limit_val = 0.0
        sources_info = []
        
        if row["limit_type"] == "fixed":
            limit_val = float(row["value"])
        else:  # percent
            if row["multi_source"] == 1 and cat_id in multi_source_links:
                # Многоисточниковая категория - считаем лимит как сумму процентов от каждого источника
                for link in multi_source_links[cat_id]:
                    source_id = link['source_id']
                    source_income = float(income_by_source.get(source_id, 0))
                    source_limit = source_income * link['percentage'] / 100.0
                    limit_val += source_limit
                    sources_info.append({
                        'source_name': link['source_name'],
                        'percentage': link['percentage'],
                        'income': source_income,
                        'limit': source_limit
                    })
            else:
                # Обычная категория - старая логика
                source_id = rule_map.get(cat_id)
                if source_id and source_id in income_by_source:
                    source_income = float(income_by_source[source_id])
                    limit_val = source_income * float(row["value"]) / 100.0
                    # Находим название источника
                    source_name = None
                    for s in sources:
                        if s["id"] == source_id:
                            source_name = s["name"]
                            break
                    sources_info.append({
                        'source_name': source_name,
                        'percentage': float(row["value"]),
                        'income': source_income,
                        'limit': limit_val
                    })
                else:
                    # Если не привязана - используем общий доход
                    limit_val = float(income_sum) * float(row["value"]) / 100.0
                    sources_info.append({
                        'source_name': 'Общий доход',
                        'percentage': float(row["value"]),
                        'income': float(income_sum),
                        'limit': limit_val
                    })

        spent = 0.0
        for s in spent_by_cat:
            if s["id"] == cat_id:
                spent = float(s["spent"])
                break

        # Получаем информацию об источнике дохода для обычных категорий (обратная совместимость)
        source_id = rule_map.get(cat_id)
        source_name = None
        if source_id and row["multi_source"] != 1:
            for s in sources:
                if s["id"] == source_id:
                    source_name = s["name"]
                    break
        
        data.append(
            dict(
                category_name=row["name"], 
                limit=limit_val, 
                spent=spent, 
                id=cat_id, 
                source_name=source_name,
                multi_source=row["multi_source"],
                sources_info=sources_info
            )
        )

    # ---- Балансы по источникам в выбранном месяце ----
    # (источники и доходы уже получены выше)

    # расход по источнику (по правилам) - обновленная логика для многоисточниковых категорий
    expense_by_source = {s["id"]: 0.0 for s in sources}
    # лимиты по источнику (сумма всех лимитов категорий, привязанных к источнику)
    limits_by_source = {s["id"]: 0.0 for s in sources}
    
    for cat in limits:
        cat_id = cat["id"]
        
        # Считаем потраченное для этой категории
        spent_val = conn.execute(
            """
            SELECT COALESCE(SUM(amount),0) FROM expenses
            WHERE user_id=? AND month=? AND category_id=?
            """,
            (uid, month, cat_id),
        ).fetchone()[0]
        spent_val = float(spent_val)
        
        if cat["multi_source"] == 1 and cat_id in multi_source_links:
            # Многоисточниковая категория - распределяем траты пропорционально лимитам
            total_limit = 0.0
            source_limits = {}
            
            # Сначала считаем общий лимит и лимит по каждому источнику
            for link in multi_source_links[cat_id]:
                source_id = link['source_id']
                if cat["limit_type"] == "fixed":
                    # Для фиксированных лимитов в многоисточниковых категориях 
                    # распределяем пропорционально процентам
                    source_limit = float(cat["value"]) * link['percentage'] / 100.0
                else:  # percent
                    source_income = float(income_by_source.get(source_id, 0))
                    source_limit = source_income * link['percentage'] / 100.0
                
                source_limits[source_id] = source_limit
                total_limit += source_limit
            
            # Распределяем траты пропорционально лимитам
            for source_id, source_limit in source_limits.items():
                if total_limit > 0:
                    proportional_spent = spent_val * (source_limit / total_limit)
                    expense_by_source[source_id] += proportional_spent
                limits_by_source[source_id] += source_limit
        else:
            # Обычная категория - старая логика
            src_id = rule_map.get(cat_id)
            if src_id:
                expense_by_source[src_id] += spent_val
                
                # Считаем лимит этой категории
                if cat["limit_type"] == "fixed":
                    limit_val = float(cat["value"])
                else:  # percent
                    source_income = float(income_by_source.get(src_id, 0))
                    limit_val = source_income * float(cat["value"]) / 100.0
                limits_by_source[src_id] += limit_val

    source_balances = []
    for s in sources:
        sid = s["id"]
        inc = float(income_by_source.get(sid, 0.0))
        sp = float(expense_by_source.get(sid, 0.0))
        limits_total = float(limits_by_source.get(sid, 0.0))
        remaining_after_limits = inc - limits_total  # остается после всех запланированных лимитов
        source_balances.append(
            dict(source_id=sid, source_name=s["name"], income=inc, spent=sp, 
                 rest=inc - sp, limits_total=limits_total, remaining_after_limits=remaining_after_limits)
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
        current_month_name=current_month_name,
        prev_month=prev_month,
        next_month=next_month,
        month_names=month_names,
        today=today,
        source_balances=source_balances,
        sources=sources,
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
    """Redirect to income page since sources are now managed there."""
    return redirect(url_for("income_page"))


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
    
    # Подсчитаем связанные записи для информации
    income_count = conn.execute(
        "SELECT COUNT(*) FROM income_daily WHERE user_id=? AND source_id=?",
        (uid, source_id)
    ).fetchone()[0]
    
    rule_count = conn.execute(
        "SELECT COUNT(*) FROM source_category_rules WHERE user_id=? AND source_id=?", 
        (uid, source_id)
    ).fetchone()[0]
    
    # Получим название источника для сообщения
    source_name = conn.execute(
        "SELECT name FROM income_sources WHERE id=? AND user_id=?",
        (source_id, uid)
    ).fetchone()
    
    if not source_name:
        conn.close()
        flash("Источник не найден", "error")
        return redirect(url_for("sources_page"))
    
    source_name = source_name[0]
    
    # Удаляем привязки к категориям (делаем их неназначенными)
    if rule_count > 0:
        conn.execute(
            "DELETE FROM source_category_rules WHERE user_id=? AND source_id=?",
            (uid, source_id)
        )
    
    # Обнуляем source_id в доходах (делаем их неназначенными)
    if income_count > 0:
        conn.execute(
            "UPDATE income_daily SET source_id=NULL WHERE user_id=? AND source_id=?",
            (uid, source_id)
        )
    
    # Удаляем источник
    conn.execute("DELETE FROM income_sources WHERE id=? AND user_id=?", (source_id, uid))
    conn.commit()
    conn.close()
    
    msg_parts = [f"Источник «{source_name}» удалён"]
    if income_count > 0:
        msg_parts.append(f"{income_count} записей доходов стали неназначенными")
    if rule_count > 0:
        msg_parts.append(f"{rule_count} категорий отвязаны от источника")
    
    flash(". ".join(msg_parts), "success")
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


@app.route("/rules/bulk-update", methods=["POST"])
@login_required
def rules_bulk_update():
    """Массовое сохранение привязок 'категория → источник' одной кнопкой."""
    uid = session["user_id"]
    # В форме придёт rules[<category_id>] = <source_id or ''>
    pairs = {}
    for k, v in request.form.items():
        if not k.startswith("rules["):
            continue
        cat_id = int(k.split("[", 1)[1].rstrip("]"))
        source_id = int(v) if v.strip() else None
        pairs[cat_id] = source_id

    conn = get_db()
    # Проверка, что категории и источники принадлежат пользователю
    for cat_id, source_id in pairs.items():
        ok_cat = conn.execute("SELECT 1 FROM categories WHERE id=? AND user_id=?", (cat_id, uid)).fetchone()
        if not ok_cat:
            continue
        existing = conn.execute(
            "SELECT id FROM source_category_rules WHERE user_id=? AND category_id=?",
            (uid, cat_id)
        ).fetchone()
        if source_id:
            ok_src = conn.execute("SELECT 1 FROM income_sources WHERE id=? AND user_id=?", (source_id, uid)).fetchone()
            if not ok_src:
                continue
            if existing:
                conn.execute("UPDATE source_category_rules SET source_id=? WHERE id=?", (source_id, existing["id"]))
            else:
                conn.execute(
                    "INSERT INTO source_category_rules(user_id, source_id, category_id) VALUES (?,?,?)",
                    (uid, source_id, cat_id)
                )
        else:
            if existing:
                conn.execute("DELETE FROM source_category_rules WHERE id=?", (existing["id"],))
    conn.commit()
    conn.close()
    flash("Привязки обновлены", "success")
    return redirect(url_for("categories"))


# -----------------------------------------------------------------------------
# Routes: categories / expenses / income
# -----------------------------------------------------------------------------
@app.route("/categories")
@login_required
def categories():
    uid = session["user_id"]
    conn = get_db()
    
    # Получаем все категории с типами и флагом multi_source
    rows = conn.execute(
        "SELECT *, COALESCE(category_type, 'expense') as category_type FROM categories WHERE user_id=? ORDER BY category_type, name", (uid,)
    ).fetchall()
    
    sources = conn.execute(
        "SELECT id, name FROM income_sources WHERE user_id=? ORDER BY name", (uid,)
    ).fetchall()
    rules = conn.execute(
        "SELECT category_id, source_id FROM source_category_rules WHERE user_id=?", (uid,)
    ).fetchall()
    rules_map = {r["category_id"]: r["source_id"] for r in rules}
    
    # Получаем связи для многоисточниковых категорий  
    multi_source_links = {}
    multi_source_rows = conn.execute("""
        SELECT category_id, source_id, percentage,
               (SELECT name FROM income_sources WHERE id = cis.source_id) as source_name
        FROM category_income_sources cis
        WHERE user_id = ?
        ORDER BY category_id, source_id
    """, (uid,)).fetchall()
    
    for link in multi_source_rows:
        cat_id = link['category_id']
        if cat_id not in multi_source_links:
            multi_source_links[cat_id] = []
        multi_source_links[cat_id].append({
            'source_id': link['source_id'],
            'source_name': link['source_name'],
            'percentage': float(link['percentage'])
        })
    
    # Разделяем категории по типам
    expense_categories = [cat for cat in rows if cat["category_type"] == "expense"]
    income_categories = [cat for cat in rows if cat["category_type"] == "income"]
    
    conn.close()
    return render_template("categories.html", 
                         categories=rows, 
                         expense_categories=expense_categories,
                         income_categories=income_categories,
                         income_sources=sources, 
                         rules_map=rules_map,
                         multi_source_links=multi_source_links)


@app.route("/categories/add", methods=["POST"])
@login_required
def categories_add():
    uid = session["user_id"]
    name = sanitize_string(request.form.get("name"))
    limit_type = request.form.get("limit_type")
    value = request.form.get("value")
    source_id = request.form.get("source_id")
    category_type = request.form.get("category_type", "expense")  # по умолчанию тратная категория

    if not name or not limit_type or not value:
        flash("Пожалуйста, заполните все поля", "error")
        return redirect(url_for("categories"))
        
    if category_type not in ["expense", "income"]:
        category_type = "expense"

    amount = validate_amount(value)
    if amount is None:
        flash("Введите корректное значение лимита", "error")
        return redirect(url_for("categories"))

    conn = get_db()
    try:
        # Создаем категорию
        multi_source = 1 if request.form.get("multi_source") else 0
        cursor = conn.execute(
            "INSERT INTO categories (user_id, name, limit_type, value, category_type, multi_source) VALUES (?,?,?,?,?,?)",
            (uid, name, limit_type, amount, category_type, multi_source),
        )
        category_id = cursor.lastrowid
        
        # Обрабатываем источники
        if multi_source == 1:
            # Многоисточниковая категория - добавляем связи из формы
            multi_sources = request.form.getlist('multi_sources')
            for i in range(len(multi_sources)):
                source_id_key = f'multi_sources[{i}][source_id]'
                percentage_key = f'multi_sources[{i}][percentage]'
                
                source_id_val = request.form.get(source_id_key)
                percentage_val = request.form.get(percentage_key)
                
                if source_id_val and percentage_val:
                    try:
                        source_id_int = int(source_id_val)
                        percentage_float = float(percentage_val)
                        
                        # Проверяем, что источник принадлежит пользователю
                        valid_source = conn.execute(
                            "SELECT 1 FROM income_sources WHERE id=? AND user_id=?",
                            (source_id_int, uid)
                        ).fetchone()
                        
                        if valid_source and 0 < percentage_float <= 100:
                            conn.execute(
                                "INSERT INTO category_income_sources(user_id, category_id, source_id, percentage) VALUES (?,?,?,?)",
                                (uid, category_id, source_id_int, percentage_float)
                            )
                    except (ValueError, TypeError):
                        continue
        elif source_id:
            # Обычная категория - создаем привязку в старой таблице
            # Проверяем, что источник принадлежит пользователю
            valid_source = conn.execute(
                "SELECT 1 FROM income_sources WHERE id=? AND user_id=?",
                (source_id, uid)
            ).fetchone()
            
            if valid_source:
                conn.execute(
                    "INSERT INTO source_category_rules(user_id, source_id, category_id) VALUES (?,?,?)",
                    (uid, source_id, category_id)
                )
        
        conn.commit()
        flash("Категория добавлена", "success")
    except sqlite3.IntegrityError:
        flash("Категория с таким названием уже существует", "error")
    finally:
        conn.close()

    return redirect(url_for("categories"))


@app.route("/categories/update/<int:cat_id>", methods=["POST"])
@login_required
def categories_update(cat_id):
    uid = session["user_id"]
    name = (request.form.get("name") or "").strip()
    limit_type = request.form.get("limit_type")
    value = request.form.get("value")
    source_id = request.form.get("source_id")

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
    
    # Обновляем категорию
    conn.execute(
        """
        UPDATE categories
           SET name=?, limit_type=?, value=?
         WHERE id=? AND user_id=?
        """,
        (name, limit_type, val, cat_id, uid),
    )
    
    # Обновляем привязку к источнику
    existing_rule = conn.execute(
        "SELECT id FROM source_category_rules WHERE user_id=? AND category_id=?",
        (uid, cat_id)
    ).fetchone()
    
    if source_id:
        # Проверяем, что источник принадлежит пользователю
        valid_source = conn.execute(
            "SELECT 1 FROM income_sources WHERE id=? AND user_id=?",
            (source_id, uid)
        ).fetchone()
        
        if valid_source:
            if existing_rule:
                conn.execute(
                    "UPDATE source_category_rules SET source_id=? WHERE id=?",
                    (source_id, existing_rule["id"])
                )
            else:
                conn.execute(
                    "INSERT INTO source_category_rules(user_id, source_id, category_id) VALUES (?,?,?)",
                    (uid, source_id, cat_id)
                )
    else:
        # Удаляем привязку, если источник не выбран
        if existing_rule:
            conn.execute(
                "DELETE FROM source_category_rules WHERE id=?",
                (existing_rule["id"],)
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
# Routes: Multi-source categories (многоисточниковые категории)
# -----------------------------------------------------------------------------

@app.route("/categories/<int:cat_id>/toggle-multi-source", methods=["POST"])
@login_required
def toggle_multi_source(cat_id):
    """Переключает режим многоисточниковости для категории."""
    uid = session["user_id"]
    conn = get_db()
    
    try:
        # Получаем текущее состояние категории
        category = conn.execute(
            "SELECT multi_source FROM categories WHERE id=? AND user_id=?",
            (cat_id, uid)
        ).fetchone()
        
        if not category:
            flash("Категория не найдена", "error")
            return redirect(url_for("categories"))
        
        new_multi_source = 1 if category["multi_source"] == 0 else 0
        
        # Переключаем режим
        conn.execute(
            "UPDATE categories SET multi_source=? WHERE id=? AND user_id=?",
            (new_multi_source, cat_id, uid)
        )
        
        if new_multi_source == 0:
            # Если выключаем многоисточниковый режим - удаляем все связи
            conn.execute(
                "DELETE FROM category_income_sources WHERE category_id=? AND user_id=?",
                (cat_id, uid)
            )
            flash("Многоисточниковый режим отключен", "success")
        else:
            flash("Многоисточниковый режим включен. Теперь можно добавить источники доходов", "success")
        
        conn.commit()
    except Exception as e:
        flash(f"Ошибка: {e}", "error")
    finally:
        conn.close()
    
    return redirect(url_for("categories"))


@app.route("/categories/<int:cat_id>/add-source", methods=["POST"])
@login_required
def add_source_to_category(cat_id):
    """Добавляет источник дохода к многоисточниковой категории."""
    uid = session["user_id"]
    source_id = request.form.get("source_id")
    percentage = request.form.get("percentage")
    
    if not source_id or not percentage:
        flash("Необходимо выбрать источник и указать процент", "error")
        return redirect(url_for("categories"))
    
    try:
        source_id = int(source_id)
        percentage = float(percentage)
        if percentage <= 0 or percentage > 100:
            raise ValueError("Процент должен быть от 0 до 100")
    except ValueError as e:
        flash(f"Некорректные данные: {e}", "error")
        return redirect(url_for("categories"))
    
    conn = get_db()
    try:
        # Проверяем, что категория многоисточниковая
        category = conn.execute(
            "SELECT multi_source FROM categories WHERE id=? AND user_id=?",
            (cat_id, uid)
        ).fetchone()
        
        if not category or category["multi_source"] != 1:
            flash("Категория не является многоисточниковой", "error")
            return redirect(url_for("categories"))
        
        # Проверяем, что источник принадлежит пользователю
        source_exists = conn.execute(
            "SELECT 1 FROM income_sources WHERE id=? AND user_id=?",
            (source_id, uid)
        ).fetchone()
        
        if not source_exists:
            flash("Источник не найден", "error")
            return redirect(url_for("categories"))
        
        # Добавляем связь
        conn.execute("""
            INSERT INTO category_income_sources (user_id, category_id, source_id, percentage)
            VALUES (?, ?, ?, ?)
        """, (uid, cat_id, source_id, percentage))
        
        conn.commit()
        flash("Источник добавлен к категории", "success")
        
    except sqlite3.IntegrityError:
        flash("Этот источник уже добавлен к данной категории", "error")
    except Exception as e:
        flash(f"Ошибка: {e}", "error")
    finally:
        conn.close()
    
    return redirect(url_for("categories"))


@app.route("/categories/<int:cat_id>/remove-source/<int:source_id>", methods=["POST"])
@login_required
def remove_source_from_category(cat_id, source_id):
    """Удаляет источник дохода из многоисточниковой категории."""
    uid = session["user_id"]
    conn = get_db()
    
    try:
        conn.execute("""
            DELETE FROM category_income_sources 
            WHERE category_id=? AND source_id=? AND user_id=?
        """, (cat_id, source_id, uid))
        
        conn.commit()
        flash("Источник удален из категории", "success")
        
    except Exception as e:
        flash(f"Ошибка: {e}", "error")
    finally:
        conn.close()
    
    return redirect(url_for("categories"))


@app.route("/categories/<int:cat_id>/update-source", methods=["POST"])
@login_required  
def update_source_percentage(cat_id):
    """Обновляет процент источника в многоисточниковой категории."""
    uid = session["user_id"]
    source_id = request.form.get("source_id")
    percentage = request.form.get("percentage")
    
    if not source_id or not percentage:
        flash("Необходимо указать источник и процент", "error")
        return redirect(url_for("categories"))
    
    try:
        source_id = int(source_id)
        percentage = float(percentage)
        if percentage <= 0 or percentage > 100:
            raise ValueError("Процент должен быть от 0 до 100")
    except ValueError as e:
        flash(f"Некорректные данные: {e}", "error")
        return redirect(url_for("categories"))
    
    conn = get_db()
    try:
        conn.execute("""
            UPDATE category_income_sources 
            SET percentage=? 
            WHERE category_id=? AND source_id=? AND user_id=?
        """, (percentage, cat_id, source_id, uid))
        
        conn.commit()
        flash("Процент обновлен", "success")
        
    except Exception as e:
        flash(f"Ошибка: {e}", "error")
    finally:
        conn.close()
    
    return redirect(url_for("categories"))


@app.route("/expenses", methods=["GET", "POST"])
@login_required
def expenses():
    uid = session["user_id"]

    if request.method == "POST":
        date_str = validate_date(request.form.get("date"))
        category_id = request.form.get("category_id")
        amount = validate_amount(request.form.get("amount"))
        note = sanitize_string(request.form.get("note"), 500)

        if not date_str or not category_id or amount is None:
            flash("Пожалуйста, заполните все обязательные поля корректно", "error")
            return redirect(url_for("expenses"))

        try:
            category_id = int(category_id)
        except (ValueError, TypeError):
            flash("Некорректная категория", "error")
            return redirect(url_for("expenses"))

        conn = get_db()
        try:
            # Сохраняем текущую валюту пользователя
            current_currency = session.get('currency', DEFAULT_CURRENCY)
            conn.execute(
                """
                INSERT INTO expenses (user_id, date, month, category_id, amount, note, currency)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (uid, date_str, date_str[:7], category_id, amount, note, current_currency),
            )
            conn.commit()
            flash("Расход добавлен", "success")
        except sqlite3.IntegrityError:
            flash("Ошибка: выбранная категория не существует", "error")
        except Exception as e:
            flash("Произошла ошибка при добавлении расхода", "error")
        finally:
            conn.close()
        return redirect(url_for("expenses"))

    # GET
    conn = get_db()
    cats = conn.execute(
        "SELECT id, name FROM categories WHERE user_id=? ORDER BY name", (uid,)
    ).fetchall()
    
    try:
        rows = conn.execute(
            """
            SELECT e.id, e.date, e.amount, e.note, e.currency, c.name AS category_name
            FROM expenses e
            JOIN categories c ON c.id = e.category_id
            WHERE e.user_id = ?
            ORDER BY e.date DESC, e.id DESC
            """,
            (uid,),
        ).fetchall()
    except sqlite3.OperationalError as e:
        if "no such column: e.currency" in str(e):
            # Fallback query without currency column
            rows = conn.execute(
                """
                SELECT e.id, e.date, e.amount, e.note, NULL AS currency, c.name AS category_name
                FROM expenses e
                JOIN categories c ON c.id = e.category_id
                WHERE e.user_id = ?
                ORDER BY e.date DESC, e.id DESC
                """,
                (uid,),
            ).fetchall()
        else:
            raise
    conn.close()
    today = datetime.now().strftime("%Y-%m-%d")
    return render_template("expenses.html", categories=cats, expenses=rows, today=today)


@app.route("/expenses/edit/<int:expense_id>", methods=["GET", "POST"])
@login_required
def edit_expense(expense_id):
    uid = session["user_id"]
    conn = get_db()
    expense = conn.execute(
        "SELECT id, date, amount, note, category_id FROM expenses WHERE id=? AND user_id=?",
        (expense_id, uid),
    ).fetchone()
    if not expense:
        conn.close()
        flash("Расход не найден", "error")
        return redirect(url_for("expenses"))

    if request.method == "POST":
        date_str = (request.form.get("date") or "").strip()
        category_id = request.form.get("category_id")
        amount_str = (request.form.get("amount") or "").strip()
        note = (request.form.get("note") or "").strip()

        if not date_str or not category_id or not amount_str:
            flash("Пожалуйста, заполните все поля", "error")
            return redirect(url_for("edit_expense", expense_id=expense_id))

        try:
            datetime.strptime(date_str, "%Y-%m-%d")
            amount = float(amount_str)
            if amount <= 0:
                raise ValueError
        except Exception:
            flash("Неверные значения даты или суммы", "error")
            return redirect(url_for("edit_expense", expense_id=expense_id))

        conn.execute(
            """
            UPDATE expenses 
            SET date=?, month=?, category_id=?, amount=?, note=?
            WHERE id=? AND user_id=?
            """,
            (date_str, date_str[:7], int(category_id), amount, note, expense_id, uid),
        )
        conn.commit()
        conn.close()
        flash("Расход обновлён", "success")
        return redirect(url_for("expenses"))

    categories = conn.execute(
        "SELECT id, name FROM categories WHERE user_id=? ORDER BY name", (uid,)
    ).fetchall()
    conn.close()
    return render_template("edit_expense.html", expense=expense, categories=categories)


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
    try:
        rows = conn.execute(
            """
            SELECT id, date, amount, source_id, currency
            FROM income_daily
            WHERE user_id = ?
            ORDER BY date DESC, id DESC
            """,
            (uid,),
        ).fetchall()
    except sqlite3.OperationalError as e:
        if "no such column: currency" in str(e):
            # Fallback query without currency column
            rows = conn.execute(
                """
                SELECT id, date, amount, source_id, NULL AS currency
                FROM income_daily
                WHERE user_id = ?
                ORDER BY date DESC, id DESC
                """,
                (uid,),
            ).fetchall()
        else:
            raise
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
    if not source_id:
        source_id = get_default_source_id(conn, uid)
    
    # Сохраняем текущую валюту пользователя
    current_currency = session.get('currency', DEFAULT_CURRENCY)
    conn.execute(
        "INSERT INTO income_daily (user_id, date, amount, source_id, currency) VALUES (?,?,?,?,?)",
        (uid, date_str, amount, source_id, current_currency),
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
# Templates
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
      <div class="d-flex gap-2 align-items-center">
        {% if session.get('user_id') %}
          <form class="d-flex align-items-center gap-1" method="post" action="{{ url_for('set_currency') }}">
            <select class="form-select form-select-sm" name="currency" id="currency-selector">
              {% for code, info in currencies.items() %}
                <option value="{{ code }}" {% if code==currency_code %}selected{% endif %}>{{ info.label }} ({{ info.symbol }})</option>
              {% endfor %}
            </select>
          </form>

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
  <script>
    // Currency conversion functionality
    let currentRates = {};
    const baseCurrency = 'RUB'; // Базовая валюта - рубли
    
    // Currency symbols mapping
    const currencySymbols = {
      'RUB': '₽',
      'USD': '$',
      'EUR': '€',
      'AMD': '֏',
      'GEL': '₾'
    };
    
    // Load exchange rates
    async function loadExchangeRates() {
      try {
        const response = await fetch('/api/exchange-rates');
        const data = await response.json();
        if (data.ok) {
          currentRates = data.rates || {};
        }
      } catch (error) {
        console.error('Failed to load exchange rates:', error);
      }
    }
    
    // Convert amount from one currency to another
    function convertAmount(amount, fromCurrency, toCurrency) {
      if (fromCurrency === toCurrency) {
        return amount;
      }
      
      // Convert to base currency (RUB) first
      let rubAmount = amount;
      if (fromCurrency !== baseCurrency) {
        const toRubRate = currentRates[`${fromCurrency}_${baseCurrency}`];
        if (toRubRate) {
          rubAmount = amount * toRubRate;
        }
      }
      
      // Convert from RUB to target currency
      if (toCurrency !== baseCurrency) {
        const fromRubRate = currentRates[`${baseCurrency}_${toCurrency}`];
        if (fromRubRate) {
          return rubAmount * fromRubRate;
        }
      }
      
      return rubAmount;
    }
    
    // Format amount with spaces for thousands
    function formatAmount(value) {
      const num = parseFloat(value);
      if (isNaN(num)) return value;
      
      // Round to 2 decimal places
      const rounded = Math.round(num * 100) / 100;
      
      // Format with spaces for thousands
      let formatted = rounded.toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g, ' ');
      
      // Remove .00 if it's a whole number
      if (formatted.endsWith(' 00')) {
        formatted = formatted.slice(0, -3);
      } else if (formatted.endsWith('00')) {
        formatted = formatted.slice(0, -3);
      }
      
      return formatted;
    }
    
    // Update all amounts on the page
    function updateAllAmounts() {
      const currentCurrency = document.querySelector('select[name="currency"]')?.value || '{{ currency_code }}';
      const currentSymbol = currencySymbols[currentCurrency] || currentCurrency;
      
      // Find all elements with data-amount and data-currency attributes
      document.querySelectorAll('[data-amount][data-currency]').forEach(element => {
        const originalAmount = parseFloat(element.getAttribute('data-amount'));
        const originalCurrency = element.getAttribute('data-currency');
        
        if (!isNaN(originalAmount) && originalCurrency) {
          const convertedAmount = convertAmount(originalAmount, originalCurrency, currentCurrency);
          element.textContent = formatAmount(convertedAmount);
        }
      });
      
      // Update currency symbols
      document.querySelectorAll('.currency-display').forEach(element => {
        element.textContent = currentSymbol;
      });
    }
    
    // Handle currency change
    document.addEventListener('DOMContentLoaded', function() {
      // Load rates on page load
      loadExchangeRates().then(() => {
        updateAllAmounts();
      });
      
      // Listen for currency changes
      const currencySelect = document.querySelector('#currency-selector');
      if (currencySelect) {
        currencySelect.addEventListener('change', function() {
          // Update amounts immediately with current rates
          updateAllAmounts();
          
          // Save currency preference to session (async)
          const selectedCurrency = this.value;
          fetch('/set-currency', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({currency: selectedCurrency})
          }).catch(error => {
            console.error('Failed to save currency preference:', error);
          });
          
          // Refresh rates in background
          loadExchangeRates();
        });
      }
    });
  </script>
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
        <div class="d-flex justify-content-between"><span>Пришло</span><strong><span data-amount="{{ s.income }}" data-currency="{{ session.currency or 'RUB' }}">{{ s.income|format_amount }}</span> <span class="currency-display">{{ currency_symbol }}</span></strong></div>
        <div class="d-flex justify-content-between"><span>Ушло</span><strong><span data-amount="{{ s.spent }}" data-currency="{{ session.currency or 'RUB' }}">{{ s.spent|format_amount }}</span> <span class="currency-display">{{ currency_symbol }}</span></strong></div>
        <div class="d-flex justify-content-between"><span>Остаток</span><strong><span data-amount="{{ s.rest }}" data-currency="{{ session.currency or 'RUB' }}">{{ s.rest|format_amount }}</span> <span class="currency-display">{{ currency_symbol }}</span></strong></div>
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
          <div class="small text-muted">
            Лимит: <span data-amount="{{ item.limit }}" data-currency="{{ session.currency or 'RUB' }}">{{ item.limit|format_amount }}</span> <span class="currency-display">{{ currency_symbol }}</span> •
            Потрачено: <span data-amount="{{ item.spent }}" data-currency="{{ session.currency or 'RUB' }}">{{ item.spent|format_amount }}</span> <span class="currency-display">{{ currency_symbol }}</span>
          </div>
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
<style>
select.form-select { position: relative; overflow: hidden; z-index: 1; }
select.form-select option { position: relative; z-index: 9999; }
</style>

<div class="d-flex justify-content-between align-items-center mb-3">
  <h2 class="h4 m-0">Категории</h2>
  <button class="btn btn-primary" data-bs-toggle="collapse" data-bs-target="#addCategoryForm">
    <i class="bi bi-plus-lg me-1"></i> Добавить категорию
  </button>
</div>

<div class="collapse mb-3" id="addCategoryForm">
  <div class="card card-body">
    <form method="POST" action="{{ url_for('categories_add') }}">
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
          <input type="number" name="value" step="0.01" min="0.01" inputmode="decimal"
                 class="form-control" placeholder="Сумма или %" required>
        </div>
        <div class="col-md-2 d-grid">
          <label class="form-label d-none d-md-block">&nbsp;</label>
          <button class="btn btn-success">Сохранить</button>
        </div>
      </div>
    </form>
  </div>
</div>

{% if not income_sources or income_sources|length == 0 %}
<div class="alert alert-info mb-3">
  Чтобы привязать категорию к источнику дохода, сначала добавьте источники на странице
  <a href="{{ url_for('sources_page') }}" class="alert-link">«Источники»</a>.
</div>
{% endif %}

<!-- ДЕСКТОП: одна общая форма для ВСЕХ привязок -->
<form method="POST" action="{{ url_for('rules_bulk_update') }}" class="table-responsive d-none d-md-block">
  <table class="table align-middle">
    <thead class="table-light">
      <tr>
        <th>Название</th>
        <th>Тип лимита</th>
        <th class="text-end">Значение</th>
        <th style="min-width:280px">Оплачивать из</th>
        <th class="text-end" style="width:220px">Действия</th>
      </tr>
    </thead>
    <tbody>
      {% for cat in categories %}
      <tr>
        <form method="POST" action="{{ url_for('categories_update', cat_id=cat.id) }}" class="d-contents">
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
            <div class="input-group input-group-sm">
              <input type="number" name="value" value="{{ cat.value }}" step="0.01" min="0.01"
                     inputmode="decimal" class="form-control form-control-sm text-end" required>
              <span class="input-group-text">
                {% if cat.limit_type == 'percent' %}%{% else %}{{ currency_symbol }}{% endif %}
              </span>
            </div>
            <div class="form-text">
              {% if cat.limit_type == 'percent' %}
                Текущ.: {{ cat.value|format_percent }}%
              {% else %}
                Текущ.: <span data-amount="{{ cat.value }}" data-currency="{{ session.currency or 'RUB' }}">{{ cat.value|format_amount }}</span> <span class="currency-display">{{ currency_symbol }}</span>
              {% endif %}
            </div>
          </td>
          <td>
            {% if income_sources and income_sources|length %}
              <select name="rules[{{ cat.id }}]" class="form-select form-select-sm">
                <option value="">(не привязано)</option>
                {% for s in income_sources %}
                  <option value="{{ s.id }}" {% if rules_map.get(cat.id) == s.id %}selected{% endif %}>{{ s.name }}</option>
                {% endfor %}
              </select>
            {% else %}
              <span class="text-muted small">Добавьте источники на странице <a href="{{ url_for('sources_page') }}">«Источники»</a></span>
            {% endif %}
          </td>
          <td class="text-end">
            <div class="btn-group btn-group-sm">
              <button type="submit" class="btn btn-outline-primary">
                <i class="bi bi-check-lg me-1"></i> Сохранить категорию
              </button>
        </form>
              <form method="POST" action="{{ url_for('categories_delete', cat_id=cat.id) }}" class="d-inline">
                <button type="submit" class="btn btn-outline-danger" onclick="return confirm('Удалить категорию «{{ cat.name }}»?')">
                  <i class="bi bi-trash3 me-1"></i> Удалить
                </button>
              </form>
            </div>
          </td>
      </tr>
      {% endfor %}
    </tbody>
    {% if income_sources and income_sources|length %}
    <tfoot>
      <tr>
        <td colspan="5" class="text-end">
          <button class="btn btn-primary">
            <i class="bi bi-plug me-1"></i> Сохранить привязки «Оплачивать из»
          </button>
        </td>
      </tr>
    </tfoot>
    {% endif %}
  </table>
</form>

<!-- МОБИЛЬНЫЕ карточки: тоже одна кнопка снизу -->
<form method="POST" action="{{ url_for('rules_bulk_update') }}" class="d-block d-md-none">
  {% for cat in categories %}
  <div class="card mb-2">
    <div class="card-body">
      <form method="POST" action="{{ url_for('categories_update', cat_id=cat.id) }}">
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
            <div class="form-text">
              {% if cat.limit_type == 'percent' %}
                Текущ.: {{ cat.value|format_percent }}%
              {% else %}
                Текущ.: <span data-amount="{{ cat.value }}" data-currency="{{ session.currency or 'RUB' }}">{{ cat.value|format_amount }}</span> <span class="currency-display">{{ currency_symbol }}</span>
              {% endif %}
            </div>
          </div>

          <div class="col-12">
            <label class="form-label">Оплачивать из</label>
            {% if income_sources and income_sources|length %}
              <select name="rules[{{ cat.id }}]" class="form-select">
                <option value="">(не привязано)</option>
                {% for s in income_sources %}
                  <option value="{{ s.id }}" {% if rules_map.get(cat.id) == s.id %}selected{% endif %}>{{ s.name }}</option>
                {% endfor %}
              </select>
            {% else %}
              <div class="form-text">Нет источников. <a href="{{ url_for('sources_page') }}">Добавить</a></div>
            {% endif %}
          </div>

          <div class="col-12 d-flex gap-2 mt-2">
            <button type="submit" formaction="{{ url_for('categories_update', cat_id=cat.id) }}" class="btn btn-outline-primary flex-fill">
              <i class="bi bi-check-lg me-1"></i> Сохранить категорию
            </button>
            <button type="submit" formaction="{{ url_for('categories_delete', cat_id=cat.id) }}" formmethod="POST"
                    class="btn btn-outline-danger flex-fill"
                    onclick="return confirm('Удалить категорию «{{ cat.name }}»?')">
              <i class="bi bi-trash3 me-1"></i> Удалить
            </button>
          </div>
        </div>
      </form>
    </div>
  </div>
  {% endfor %}

  {% if income_sources and income_sources|length %}
  <div class="sticky-bottom bg-white py-2">
    <button class="btn btn-primary w-100">
      <i class="bi bi-plug me-1"></i> Сохранить все привязки
    </button>
  </div>
  {% endif %}
</form>
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
    <form method="POST" action="{{ url_for('expenses') }}">
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
        <td class="text-end fw-semibold">
          <span data-amount="{{ e.amount }}" data-currency="{{ e.currency or 'RUB' }}">{{ e.amount|format_amount }}</span> 
          <span class="currency-display">{{ currency_symbol }}</span>
        </td>
        <td>{{ e.note or '' }}</td>
        <td class="text-end">
          <form method="POST" action="{{ url_for('delete_expense', expense_id=e.id) }}" class="d-inline">
            <button class="btn btn-sm btn-outline-danger" onclick="return confirm('Удалить расход?\\nДата: {{ e.date|format_date_with_day }}\\nКатегория: {{ e.category_name }}\\nСумма: {{ e.amount|format_amount }} {{ e.currency or session.currency or 'RUB' }}')">Удалить</button>
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
        <td class="text-end fw-semibold">
          <span data-amount="{{ i.amount }}" data-currency="{{ i.currency or 'RUB' }}">{{ i.amount|format_amount }}</span>
          <span class="currency-display">{{ currency_symbol }}</span>
        </td>
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

ACCOUNT_HTML = """
{% extends "base.html" %}
{% block title %}Личный кабинет — CrystalBudget{% endblock %}
{% block content %}
<div class="row g-4">
  <div class="col-md-4">
    <div class="card modern-card">
      <div class="card-body">
        <h5 class="card-title mb-3">Аватар</h5>
        <div class="text-center mb-3">
          {% if user.avatar_path %}
            <img src="{{ url_for('static', filename=user.avatar_path) }}" alt="avatar" class="rounded-circle" style="width:120px;height:120px;object-fit:cover;">
          {% else %}
            <div class="rounded-circle bg-secondary d-inline-flex align-items-center justify-content-center" style="width:120px;height:120px;color:#fff;font-size:40px;">
              {{ (user.name or 'U')[:1] }}
            </div>
          {% endif %}
        </div>
        <form method="post" action="{{ url_for('account_avatar') }}" enctype="multipart/form-data">
          <div class="mb-3">
            <input class="form-control" type="file" name="avatar" accept=".png,.jpg,.jpeg,.webp" required>
            <div class="form-text">До 2 МБ</div>
          </div>
          <button class="btn btn-outline-primary w-100">Загрузить</button>
        </form>
      </div>
    </div>
  </div>

  <div class="col-md-8">
    <div class="card modern-card mb-4">
      <div class="card-body">
        <h5 class="card-title mb-3">Профиль</h5>
        <form method="post" action="{{ url_for('account') }}">
          <div class="row g-3">
            <div class="col-md-6">
              <label class="form-label">Имя</label>
              <input class="form-control" name="name" value="{{ user.name or '' }}" required>
            </div>
            <div class="col-md-6">
              <label class="form-label">Email</label>
              <input class="form-control" type="email" name="email" value="{{ user.email or '' }}" required>
            </div>
            {% if user.timezone is defined %}
            <div class="col-md-4">
              <label class="form-label">Часовой пояс</label>
              <input class="form-control" name="timezone" value="{{ user.timezone or 'UTC' }}" placeholder="Europe/Moscow">
            </div>
            <div class="col-md-4">
              <label class="form-label">Язык</label>
              <select class="form-select" name="locale">
                <option value="ru" {% if (user.locale or 'ru')=='ru' %}selected{% endif %}>Русский</option>
                <option value="en" {% if user.locale=='en' %}selected{% endif %}>English</option>
              </select>
            </div>
            <div class="col-md-4">
              <label class="form-label">Валюта по умолчанию</label>
              <select class="form-select" name="default_currency">
                {% for code, info in currencies.items() %}
                  <option value="{{ code }}" {% if (user.default_currency or 'RUB') == code %}selected{% endif %}>{{ info.label }} ({{ info.symbol }})</option>
                {% endfor %}
              </select>
            </div>
            <div class="col-md-4">
              <label class="form-label">Тема</label>
              <select class="form-select" name="theme">
                <option value="light" {% if (user.theme or 'light')=='light' %}selected{% endif %}>Светлая</option>
                <option value="dark" {% if user.theme=='dark' %}selected{% endif %}>Тёмная</option>
              </select>
            </div>
            {% else %}
            <div class="col-12">
              <div class="alert alert-info">
                <i class="bi bi-info-circle"></i> 
                Дополнительные настройки профиля будут доступны после обновления системы.
              </div>
            </div>
            {% endif %}
            <div class="col-12 d-flex gap-2 mt-2">
              <button class="btn btn-primary">Сохранить</button>
              <a class="btn btn-secondary" href="{{ url_for('dashboard') }}">Отмена</a>
            </div>
          </div>
        </form>
      </div>
    </div>

    <div class="card modern-card">
      <div class="card-body">
        <h5 class="card-title mb-3">Смена пароля</h5>
        <form method="post" action="{{ url_for('account_password') }}">
          <div class="row g-3">
            <div class="col-md-4">
              <label class="form-label">Текущий пароль</label>
              <input class="form-control" type="password" name="old_password" required>
            </div>
            <div class="col-md-4">
              <label class="form-label">Новый пароль</label>
              <input class="form-control" type="password" name="new_password" minlength="6" required>
            </div>
            <div class="col-md-4">
              <label class="form-label">Повторите новый</label>
              <input class="form-control" type="password" name="confirm_password" minlength="6" required>
            </div>
            <div class="col-12 mt-2">
              <button class="btn btn-outline-primary">Обновить пароль</button>
            </div>
          </div>
        </form>
      </div>
    </div>

  </div>
</div>
{% endblock %}
"""

app.jinja_loader = ChoiceLoader(
    [
        app.jinja_loader,  # ← сначала файловая система
        DictLoader({
            "base.html": BASE_HTML,
            "login.html": LOGIN_HTML,
            "register.html": REGISTER_HTML,
            "dashboard.html": DASHBOARD_HTML,
            # "categories.html": CATEGORIES_HTML,  # ← убрано!
            "expenses.html": EXPENSES_HTML,
            "income.html": INCOME_HTML,
            "sources.html": SOURCES_HTML,
            "account.html": ACCOUNT_HTML,
        }),
    ]
)


# -----------------------------------------------------------------------------
# Health check endpoint для мониторинга
# -----------------------------------------------------------------------------
@app.route('/health')
def health_check():
    """Simple health check endpoint for monitoring."""
    try:
        # Проверяем подключение к базе данных
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        conn.close()
        
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "version": "1.0"
        }, 200
    except Exception as e:
        app.logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy", 
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }, 503

# -----------------------------------------------------------------------------
# Analytics and Charts API
# -----------------------------------------------------------------------------

@app.route('/api/expenses/chart-data')
@login_required
def expenses_chart_data():
    """API endpoint for expense charts data."""
    try:
        period = request.args.get('period', '6months')  # 6months, year, all
        chart_type = request.args.get('type', 'monthly')  # monthly, category, daily
        
        conn = get_db()
        user_id = session['user_id']
        
        if chart_type == 'monthly':
            # Данные по месяцам за выбранный период
            if period == '6months':
                query = """
                SELECT strftime('%Y-%m', date) as month, SUM(amount) as total
                FROM expenses 
                WHERE user_id = ? AND date >= date('now', '-6 months')
                GROUP BY strftime('%Y-%m', date)
                ORDER BY month
                """
            elif period == 'year':
                query = """
                SELECT strftime('%Y-%m', date) as month, SUM(amount) as total
                FROM expenses 
                WHERE user_id = ? AND date >= date('now', '-1 year')
                GROUP BY strftime('%Y-%m', date)
                ORDER BY month
                """
            else:  # all
                query = """
                SELECT strftime('%Y-%m', date) as month, SUM(amount) as total
                FROM expenses 
                WHERE user_id = ?
                GROUP BY strftime('%Y-%m', date)
                ORDER BY month
                """
            
            cursor = conn.execute(query, (user_id,))
            
        elif chart_type == 'category':
            # Данные по категориям за текущий месяц
            query = """
            SELECT c.name, COALESCE(SUM(e.amount), 0) as total
            FROM categories c
            LEFT JOIN expenses e ON c.id = e.category_id AND strftime('%Y-%m', e.date) = strftime('%Y-%m', 'now')
            WHERE c.user_id = ?
            GROUP BY c.id, c.name
            ORDER BY total DESC
            """
            cursor = conn.execute(query, (user_id,))
            
        data = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return {"success": True, "data": data}
        
    except Exception as e:
        app.logger.error(f"Error in expenses_chart_data: {e}")
        return {"success": False, "error": str(e)}, 500

@app.route('/api/expenses/compare')
@login_required
def expenses_compare():
    """API для сравнения периодов."""
    try:
        current_month = datetime.now().strftime('%Y-%m')
        prev_month = (datetime.now().replace(day=1) - timedelta(days=1)).strftime('%Y-%m')
        
        conn = get_db()
        user_id = session['user_id']
        
        # Сравнение текущего и предыдущего месяца по категориям
        query = """
        SELECT 
            c.name,
            COALESCE(SUM(CASE WHEN strftime('%Y-%m', e.date) = ? THEN e.amount ELSE 0 END), 0) as current_month,
            COALESCE(SUM(CASE WHEN strftime('%Y-%m', e.date) = ? THEN e.amount ELSE 0 END), 0) as prev_month
        FROM categories c
        LEFT JOIN expenses e ON c.id = e.category_id 
        WHERE c.user_id = ?
        GROUP BY c.id, c.name
        ORDER BY current_month DESC
        """
        
        cursor = conn.execute(query, (current_month, prev_month, user_id))
        data = []
        
        for row in cursor.fetchall():
            current = float(row['current_month'])
            prev = float(row['prev_month'])
            change_percent = 0
            if prev > 0:
                change_percent = ((current - prev) / prev) * 100
                
            data.append({
                'category': row['name'],
                'current_month': current,
                'prev_month': prev,
                'change_percent': round(change_percent, 1)
            })
            
        conn.close()
        
        return {
            "success": True, 
            "data": data,
            "period": {
                "current": current_month,
                "previous": prev_month
            }
        }
        
    except Exception as e:
        app.logger.error(f"Error in expenses_compare: {e}")
        return {"success": False, "error": str(e)}, 500

@app.route('/api/convert')
@login_required
def api_convert():
    """API для конвертации валют."""
    amount = request.args.get('amount', type=float)
    from_curr = request.args.get('from', '').upper()
    to_curr = request.args.get('to', '').upper()
    
    if not amount or not from_curr or not to_curr:
        return {"ok": False, "error": "Missing parameters"}, 400
    
    try:
        converted_amount = convert_currency(amount, from_curr, to_curr)
        rate = get_exchange_rate(from_curr, to_curr)
        
        return {
            "ok": True,
            "amount": amount,
            "from": from_curr,
            "to": to_curr,
            "converted": converted_amount,
            "rate": rate
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}, 500

@app.route('/api/exchange-rates')
@login_required 
def get_exchange_rates():
    """API для получения курсов валют."""
    try:
        conn = get_db()
        
        # Проверяем кэш курсов (обновляем раз в час)
        cursor = conn.execute("""
        SELECT from_currency, to_currency, rate, updated_at 
        FROM exchange_rates 
        WHERE updated_at > datetime('now', '-1 hour')
        """)
        
        cached_rates = {}
        for row in cursor.fetchall():
            key = f"{row['from_currency']}_{row['to_currency']}"
            cached_rates[key] = float(row['rate'])
        
        # Если кэш пуст или нет нужных курсов, загружаем свежие данные
        currencies = ['RUB', 'USD', 'EUR', 'AMD', 'GEL']
        needed_pairs = []
        
        for from_curr in currencies:
            for to_curr in currencies:
                if from_curr != to_curr:
                    key = f"{from_curr}_{to_curr}"
                    if key not in cached_rates:
                        needed_pairs.append((from_curr, to_curr))
        
        # Загружаем недостающие курсы
        if needed_pairs:
            for from_curr, to_curr in needed_pairs:
                try:
                    rate = get_exchange_rate(from_curr, to_curr)
                    if rate and rate > 0:
                        cached_rates[f"{from_curr}_{to_curr}"] = rate
                except Exception as e:
                    app.logger.warning(f"Failed to get rate {from_curr}->{to_curr}: {e}")
        
        conn.close()
        
        return {"ok": True, "rates": cached_rates}
        
    except Exception as e:
        app.logger.error(f"Error in get_exchange_rates: {e}")
        return {"ok": False, "error": str(e)}, 500

# -----------------------------------------------------------------------------
# Savings Goals
# -----------------------------------------------------------------------------

@app.route('/goals')
@login_required
def goals():
    """Страница целей накоплений."""
    conn = get_db()
    user_id = session['user_id']
    
    # Получаем все цели пользователя
    cursor = conn.execute("""
    SELECT * FROM savings_goals 
    WHERE user_id = ? 
    ORDER BY created_at DESC
    """, (user_id,))
    
    goals = cursor.fetchall()
    conn.close()
    
    return render_template('goals.html', goals=goals)

@app.route('/goals/add', methods=['POST'])
@login_required
def add_goal():
    """Добавление новой цели накопления."""
    try:
        name = request.form.get('name', '').strip()
        target_amount = float(request.form.get('target_amount', 0))
        target_date = request.form.get('target_date', '')
        description = request.form.get('description', '').strip()
        
        if not name or target_amount <= 0:
            flash('Название и сумма цели обязательны', 'error')
            return redirect(url_for('goals'))
            
        conn = get_db()
        user_id = session['user_id']
        
        conn.execute("""
        INSERT INTO savings_goals (user_id, name, target_amount, target_date, description)
        VALUES (?, ?, ?, ?, ?)
        """, (user_id, name, target_amount, target_date if target_date else None, description))
        
        conn.commit()
        conn.close()
        
        flash(f'Цель "{name}" добавлена', 'success')
        
    except Exception as e:
        app.logger.error(f"Error adding goal: {e}")
        flash('Ошибка при добавлении цели', 'error')
        
    return redirect(url_for('goals'))

@app.route('/goals/update/<int:goal_id>', methods=['POST'])
@login_required
def update_goal_progress(goal_id):
    """Обновление прогресса цели."""
    try:
        amount_to_add = float(request.form.get('amount', 0))
        
        if amount_to_add <= 0:
            flash('Сумма должна быть положительной', 'error')
            return redirect(url_for('goals'))
            
        conn = get_db()
        user_id = session['user_id']
        
        # Проверяем, что цель принадлежит пользователю
        cursor = conn.execute("""
        SELECT current_amount, target_amount FROM savings_goals 
        WHERE id = ? AND user_id = ?
        """, (goal_id, user_id))
        
        goal = cursor.fetchone()
        if not goal:
            flash('Цель не найдена', 'error')
            return redirect(url_for('goals'))
            
        new_amount = float(goal['current_amount']) + amount_to_add
        
        # Проверяем, достигнута ли цель
        completed_at = None
        if new_amount >= float(goal['target_amount']):
            completed_at = datetime.now().isoformat()
            
        conn.execute("""
        UPDATE savings_goals 
        SET current_amount = ?, completed_at = ?
        WHERE id = ? AND user_id = ?
        """, (new_amount, completed_at, goal_id, user_id))
        
        conn.commit()
        conn.close()
        
        if completed_at:
            flash('🎉 Поздравляем! Цель достигнута!', 'success')
        else:
            flash(f'Добавлено {amount_to_add} к цели', 'success')
            
    except Exception as e:
        app.logger.error(f"Error updating goal progress: {e}")
        flash('Ошибка при обновлении прогресса', 'error')
        
    return redirect(url_for('goals'))

# -----------------------------------------------------------------------------  
# Shared Budgets
# -----------------------------------------------------------------------------

@app.route('/shared-budgets')
@login_required
def shared_budgets():
    """Страница семейных бюджетов."""
    conn = get_db()
    user_id = session['user_id']
    
    # Получаем бюджеты, в которых участвует пользователь
    cursor = conn.execute("""
    SELECT sb.*, sbm.role, sbm.joined_at,
           (SELECT COUNT(*) FROM shared_budget_members WHERE shared_budget_id = sb.id) as member_count
    FROM shared_budgets sb
    JOIN shared_budget_members sbm ON sb.id = sbm.shared_budget_id
    WHERE sbm.user_id = ?
    ORDER BY sbm.joined_at DESC
    """, (user_id,))
    
    shared_budgets_list = cursor.fetchall()
    conn.close()
    
    return render_template('shared_budgets.html', shared_budgets=shared_budgets_list)

@app.route('/shared-budgets/create', methods=['POST'])
@login_required
def create_shared_budget():
    """Создание нового семейного бюджета."""
    try:
        name = request.form.get('name', '').strip()
        
        if not name:
            flash('Название бюджета обязательно', 'error')
            return redirect(url_for('shared_budgets'))
        
        conn = get_db()
        user_id = session['user_id']
        
        # Генерируем уникальный код приглашения
        import secrets
        invite_code = secrets.token_urlsafe(8)
        
        # Создаем shared budget
        cursor = conn.execute("""
        INSERT INTO shared_budgets (name, creator_id, invite_code)
        VALUES (?, ?, ?)
        """, (name, user_id, invite_code))
        
        shared_budget_id = cursor.lastrowid
        
        # Добавляем создателя как администратора
        conn.execute("""
        INSERT INTO shared_budget_members (shared_budget_id, user_id, role)
        VALUES (?, ?, 'admin')
        """, (shared_budget_id, user_id))
        
        conn.commit()
        conn.close()
        
        flash(f'Семейный бюджет "{name}" создан. Код для приглашения: {invite_code}', 'success')
        
    except Exception as e:
        app.logger.error(f"Error creating shared budget: {e}")
        flash('Ошибка при создании семейного бюджета', 'error')
        
    return redirect(url_for('shared_budgets'))

@app.route('/shared-budgets/join', methods=['POST'])
@login_required 
def join_shared_budget():
    """Присоединение к семейному бюджету по коду."""
    try:
        invite_code = request.form.get('invite_code', '').strip()
        
        if not invite_code:
            flash('Код приглашения обязателен', 'error')
            return redirect(url_for('shared_budgets'))
            
        conn = get_db()
        user_id = session['user_id']
        
        # Находим бюджет по коду
        cursor = conn.execute("""
        SELECT id, name FROM shared_budgets 
        WHERE invite_code = ?
        """, (invite_code,))
        
        budget = cursor.fetchone()
        if not budget:
            flash('Неверный код приглашения', 'error')
            return redirect(url_for('shared_budgets'))
        
        # Проверяем, что пользователь еще не участвует
        cursor = conn.execute("""
        SELECT id FROM shared_budget_members 
        WHERE shared_budget_id = ? AND user_id = ?
        """, (budget['id'], user_id))
        
        if cursor.fetchone():
            flash('Вы уже участвуете в этом бюджете', 'warning')
            return redirect(url_for('shared_budgets'))
        
        # Добавляем пользователя
        conn.execute("""
        INSERT INTO shared_budget_members (shared_budget_id, user_id, role)
        VALUES (?, ?, 'member')
        """, (budget['id'], user_id))
        
        conn.commit()
        conn.close()
        
        flash(f'Вы присоединились к семейному бюджету "{budget["name"]}"', 'success')
        
    except Exception as e:
        app.logger.error(f"Error joining shared budget: {e}")
        flash('Ошибка при присоединении к бюджету', 'error')
        
    return redirect(url_for('shared_budgets'))

@app.route('/shared-budgets/<int:budget_id>')
@login_required
def shared_budget_detail(budget_id):
    """Детали семейного бюджета."""
    conn = get_db()
    user_id = session['user_id']
    
    # Проверяем доступ
    cursor = conn.execute("""
    SELECT sb.*, sbm.role
    FROM shared_budgets sb
    JOIN shared_budget_members sbm ON sb.id = sbm.shared_budget_id
    WHERE sb.id = ? AND sbm.user_id = ?
    """, (budget_id, user_id))
    
    budget = cursor.fetchone()
    if not budget:
        flash('Бюджет не найден или у вас нет доступа', 'error')
        return redirect(url_for('shared_budgets'))
    
    # Получаем участников
    cursor = conn.execute("""
    SELECT u.name AS username, sbm.role, sbm.joined_at
    FROM shared_budget_members sbm
    JOIN users u ON sbm.user_id = u.id
    WHERE sbm.shared_budget_id = ?
    ORDER BY sbm.joined_at ASC
    """, (budget_id,))
    
    members = cursor.fetchall()
    
    # Получаем общие расходы всех участников за текущий месяц
    cursor = conn.execute("""
    SELECT e.amount, e.note AS description, e.date, c.name AS category_name, u.name AS username
    FROM expenses e
    JOIN categories c ON e.category_id = c.id
    JOIN users u ON e.user_id = u.id
    JOIN shared_budget_members sbm ON u.id = sbm.user_id
    WHERE sbm.shared_budget_id = ? 
    AND strftime('%Y-%m', e.date) = strftime('%Y-%m', 'now')
    ORDER BY e.date DESC, e.id DESC
    LIMIT 50
    """, (budget_id,))
    
    recent_expenses = cursor.fetchall()
    
    conn.close()
    
    return render_template('shared_budget_detail.html', 
                         budget=budget, 
                         members=members, 
                         recent_expenses=recent_expenses)
@app.after_request
def set_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'

    csp_base = [
        "default-src 'self'",
        "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net",
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdn.jsdelivr.net",
        "font-src 'self' data: https://fonts.gstatic.com https://cdn.jsdelivr.net",
        "img-src 'self' data:",
        "connect-src 'self' https://api.exchangerate.host"
    ]

    response.headers['Content-Security-Policy'] = "; ".join(csp_base)

    # HSTS только если у тебя включён HTTPS (можно завязать на переменную окружения)
    if os.environ.get('HTTPS_MODE', 'false').lower() == 'true':
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'

    if request.endpoint == 'static':
        response.headers['Cache-Control'] = 'public, max-age=86400'
    return response
def add_profile_columns_if_missing():
    """Добавляем поля профиля в таблицу users если их нет."""
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(users)")
        cols = {r[1] for r in cur.fetchall()}

        def add(col_sql):
            try:
                cur.execute(col_sql)
            except sqlite3.OperationalError:
                pass

        if "timezone" not in cols:
            add("ALTER TABLE users ADD COLUMN timezone TEXT DEFAULT 'UTC'")
        if "locale" not in cols:
            add("ALTER TABLE users ADD COLUMN locale TEXT DEFAULT 'ru'")
        if "default_currency" not in cols:
            add("ALTER TABLE users ADD COLUMN default_currency TEXT DEFAULT 'RUB'")
        if "theme" not in cols:
            add("ALTER TABLE users ADD COLUMN theme TEXT DEFAULT 'light'")
        if "avatar_path" not in cols:
            add("ALTER TABLE users ADD COLUMN avatar_path TEXT")
        if "currency" not in cols:
            add("ALTER TABLE users ADD COLUMN currency TEXT DEFAULT 'RUB'")

        conn.commit()
        conn.close()
        app.logger.info("Profile columns migration completed successfully")
        
    except Exception as e:
        app.logger.error(f"Error in add_profile_columns_if_missing migration: {e}")
        if conn:
            conn.close()

def ensure_new_tables():
    """Создаем новые таблицы если их нет (миграция)."""
    try:
        conn = get_db()
        
        # Проверяем существование таблиц
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='savings_goals'")
        if not cursor.fetchone():
            # Таблица для целей накоплений
            conn.execute("""
            CREATE TABLE savings_goals (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
              name TEXT NOT NULL,
              target_amount DECIMAL(10,2) NOT NULL,
              current_amount DECIMAL(10,2) DEFAULT 0,
              target_date DATE,
              created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
              completed_at TIMESTAMP NULL,
              description TEXT
            )
            """)
            app.logger.info("Created savings_goals table")
        
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='shared_budgets'")
        if not cursor.fetchone():
            # Таблица для shared budgets
            conn.execute("""
            CREATE TABLE shared_budgets (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              name TEXT NOT NULL,
              creator_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
              invite_code TEXT UNIQUE NOT NULL,
              created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
            app.logger.info("Created shared_budgets table")
        
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='shared_budget_members'")
        if not cursor.fetchone():
            # Участники shared budgets
            conn.execute("""
            CREATE TABLE shared_budget_members (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              shared_budget_id INTEGER NOT NULL REFERENCES shared_budgets(id) ON DELETE CASCADE,
              user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
              role TEXT DEFAULT 'member',
              joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
              UNIQUE(shared_budget_id, user_id)
            )
            """)
            app.logger.info("Created shared_budget_members table")
        
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='exchange_rates'")
        if not cursor.fetchone():
            # Курсы валют (для кэширования)
            conn.execute("""
            CREATE TABLE exchange_rates (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              from_currency TEXT NOT NULL,
              to_currency TEXT NOT NULL,
              rate DECIMAL(10,6) NOT NULL,
              updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
              UNIQUE(from_currency, to_currency)
            )
            """)
            app.logger.info("Created exchange_rates table")
            
        conn.commit()
        conn.close()
        app.logger.info("New tables migration completed successfully")
        
    except Exception as e:
        app.logger.error(f"Error in ensure_new_tables migration: {e}")
        if conn:
            conn.close()

# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    init_db()
    ensure_income_sources_tables()
    migrate_income_to_daily_if_needed()
    add_source_id_column_if_missing()
    add_category_type_column_if_missing()
    add_currency_columns_if_missing()
    add_profile_columns_if_missing()  # Миграция полей профиля
    ensure_new_tables()  # Миграция новых таблиц
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=os.environ.get("FLASK_ENV") == "development")