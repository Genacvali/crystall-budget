import os
import sqlite3
import logging
import requests
import smtplib
import secrets
import hashlib
import hmac
import time
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from functools import wraps
from logging.handlers import RotatingFileHandler
from email.mime_text import MIMEText
from email.mime_multipart import MIMEMultipart
from urllib.parse import urlparse  # <-- для safe next

# Load environment variables from .env file (optional)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from flask import (
    Flask, render_template, render_template_string, request, redirect,
    url_for, flash, session, abort
)
from jinja2 import DictLoader, ChoiceLoader
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

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
    app.config['SESSION_COOKIE_NAME'] = 'cb_session'
    app.config['WTF_CSRF_TIME_LIMIT'] = 3600
else:
    app.config['SESSION_COOKIE_NAME'] = 'session'

DB_PATH = os.environ.get("BUDGET_DB", "budget.db")
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_BOT_USERNAME = os.environ.get("TELEGRAM_BOT_USERNAME", "crystalbudget_bot")

# -----------------------------------------------------------------------------
# Telegram authentication helpers
# -----------------------------------------------------------------------------
TG_KEYS = ("auth_date", "first_name", "id", "last_name", "photo_url", "username")

def verify_telegram_auth(args, bot_token: str, max_age_sec: int = 600) -> bool:
    """Проверяет подпись Telegram и давность auth_date."""
    tg_hash = args.get("hash")
    if not tg_hash:
        app.logger.warning("No hash in Telegram data")
        return False

    pairs = [f"{k}={args.get(k)}" for k in sorted(TG_KEYS) if args.get(k) is not None]
    data_check_string = "\n".join(pairs)

    secret = hashlib.sha256(bot_token.encode()).digest()
    calc = hmac.new(secret, data_check_string.encode(), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(calc, tg_hash):
        app.logger.warning("TG hash mismatch")
        return False

    try:
        time_diff = time.time() - int(args.get("auth_date", "0"))
        if time_diff > max_age_sec:
            app.logger.warning(f"TG auth too old: {time_diff} > {max_age_sec}")
            return False
    except ValueError:
        app.logger.warning("TG invalid auth_date")
        return False

    return True

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
    log_dir = os.path.join(os.path.dirname(__file__), 'logs')
    os.makedirs(log_dir, exist_ok=True)

    log_file = os.path.join(log_dir, 'crystalbudget.log')
    file_handler = RotatingFileHandler(log_file, maxBytes=10*1024*1024, backupCount=5)

    formatter = logging.Formatter('%(asctime)s %(levelname)s [%(name)s] %(message)s')
    file_handler.setFormatter(formatter)

    log_level = os.environ.get('LOG_LEVEL', 'INFO').upper()
    file_handler.setLevel(getattr(logging, log_level))

    app.logger.addHandler(file_handler)
    app.logger.setLevel(getattr(logging, log_level))

    werkzeug_logger = logging.getLogger('werkzeug')
    werkzeug_logger.addHandler(file_handler)
    werkzeug_logger.setLevel(logging.INFO)

    app.logger.info('Logging initialized')

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
EXR_CACHE_TTL_SECONDS = int(os.environ.get("EXR_CACHE_TTL_SECONDS", str(12 * 3600)))
EXR_BRIDGE = os.environ.get("EXR_BRIDGE", "USD").upper()

@app.context_processor
def inject_currency():
    code = session.get("currency", DEFAULT_CURRENCY)
    info = CURRENCIES.get(code, CURRENCIES[DEFAULT_CURRENCY])
    return dict(currency_code=code, currency_symbol=info["symbol"], currencies=CURRENCIES)

# -----------------------------------------------------------------------------
# Currency conversion helper
# -----------------------------------------------------------------------------
BRIDGE_CURRENCY = EXR_BRIDGE

def _norm_cur(curr):
    return str(curr).strip().upper()

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def get_exchange_rate_via_bridge(frm: str, to: str, bridge: str = BRIDGE_CURRENCY) -> float:
    import requests
    frm, to, bridge = _norm_cur(frm), _norm_cur(to), _norm_cur(bridge)
    if frm == to:
        return 1.0
    url = "https://api.exchangerate.host/latest"
    if frm == bridge:
        r = requests.get(url, params={"base": bridge, "symbols": to}, timeout=6)
        r.raise_for_status()
        return float(r.json()["rates"][to])
    if to == bridge:
        r = requests.get(url, params={"base": frm, "symbols": bridge}, timeout=6)
        r.raise_for_status()
        return float(r.json()["rates"][bridge])
    r1 = requests.get(url, params={"base": frm, "symbols": bridge}, timeout=6).json()["rates"][bridge]
    r2 = requests.get(url, params={"base": bridge, "symbols": to}, timeout=6).json()["rates"][to]
    return float(r1) * float(r2)

def _fetch_rate_exchangerate_host(frm: str, to: str) -> float:
    import requests
    url = "https://api.exchangerate.host/convert"
    r = requests.get(url, params={"from": frm, "to": to}, timeout=6)
    r.raise_for_status()
    data = r.json()
    if not data or "result" not in data or not data["result"]:
        raise ValueError("no result from exchangerate.host")
    return float(data["result"])

def get_exchange_rate(frm: str, to: str) -> float:
    from datetime import datetime, timedelta
    frm, to = _norm_cur(frm), _norm_cur(to)
    if frm == to:
        return 1.0

    now = datetime.utcnow()
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT rate, updated_at FROM exchange_rates WHERE from_currency=? AND to_currency=?",
            (frm, to)
        ).fetchone()

        if row:
            try:
                updated = datetime.fromisoformat((row["updated_at"] or "").replace("Z", ""))
            except Exception:
                updated = now - timedelta(days=365)
            if (now - updated).total_seconds() < EXR_CACHE_TTL_SECONDS and row["rate"] and row["rate"] > 0:
                return float(row["rate"])

        try:
            rate = _fetch_rate_exchangerate_host(frm, to)
        except Exception:
            rate = None

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
                (frm, to, float(rate), now.isoformat(timespec="seconds") + "Z"),
            )
            conn.commit()
            return float(rate)

        if row and row["rate"]:
            return float(row["rate"])

        raise RuntimeError(f"cannot fetch exchange rate {frm}->{to}")
    except Exception as e:
        app.logger.error(f"Exchange rate error {frm}->{to}: {e}")
        return 1.0
    finally:
        conn.close()

def convert_currency(amount, from_currency, to_currency):
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
    try:
        if from_currency and 'currency' in session:
            target_currency = session['currency']
            if from_currency != target_currency:
                value = convert_currency(value, from_currency, target_currency)
        d = Decimal(str(value))
    except Exception:
        return str(value)
    q = d.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    s = f"{q:,.2f}".replace(",", " ")
    return s[:-3] if s.endswith("00") else s

@app.template_filter("format_percent")
def format_percent(value):
    try:
        v = float(value)
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
    if not amount_str or not amount_str.strip():
        return None
    try:
        amount = float(amount_str.strip())
        return amount if amount > 0 else None
    except (ValueError, TypeError):
        return None

def validate_date(date_str):
    if not date_str or not date_str.strip():
        return None
    try:
        datetime.strptime(date_str.strip(), "%Y-%m-%d")
        return date_str.strip()
    except ValueError:
        return None

def sanitize_string(s, max_length=255):
    if not s:
        return ""
    return str(s).strip()[:max_length]

def generate_months_list(current_month=None):
    if not current_month:
        current_month = datetime.now().strftime("%Y-%m")
    current_year = int(current_month.split('-')[0])
    start_year = current_year - 2
    end_year = current_year + 1
    month_names_ru = [
        "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
        "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"
    ]
    months = []
    for year in range(start_year, end_year + 1):
        for month in range(1, 13):
            ym = f"{year}-{month:02d}"
            month_name = month_names_ru[month - 1]
            months.append({
                'y': year, 'm': month, 'ym': ym,
                'label': f"{month_name} {year}",
                'url': f"?month={ym}"
            })
    return months

# -----------------------------------------------------------------------------
# DB helpers (schema & migrations trimmed to essentials to keep file focused)
# -----------------------------------------------------------------------------
def init_db():
    conn = get_db()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE,
            name TEXT NOT NULL,
            password_hash TEXT,
            auth_type TEXT DEFAULT 'email',
            telegram_id INTEGER UNIQUE,
            telegram_username TEXT,
            telegram_first_name TEXT,
            telegram_last_name TEXT,
            telegram_photo_url TEXT,
            timezone TEXT DEFAULT 'UTC',
            locale TEXT DEFAULT 'ru',
            default_currency TEXT DEFAULT 'RUB',
            currency TEXT DEFAULT 'RUB',
            theme TEXT DEFAULT 'light',
            avatar_path TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            name TEXT NOT NULL,
            limit_type TEXT NOT NULL CHECK(limit_type IN ('fixed','percent')),
            value REAL NOT NULL,
            category_type TEXT DEFAULT 'expense' CHECK(category_type IN ('expense','income')),
            multi_source INTEGER DEFAULT 0,
            UNIQUE(user_id, name)
        );

        CREATE TABLE IF NOT EXISTS income_daily (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            date TEXT NOT NULL,
            amount REAL NOT NULL,
            source_id INTEGER REFERENCES income_sources(id),
            currency TEXT DEFAULT 'RUB'
        );

        CREATE TABLE IF NOT EXISTS income_sources (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          name TEXT NOT NULL,
          is_default INTEGER NOT NULL DEFAULT 0,
          UNIQUE(user_id, name)
        );

        CREATE TABLE IF NOT EXISTS source_category_rules (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          source_id INTEGER NOT NULL REFERENCES income_sources(id) ON DELETE CASCADE,
          category_id INTEGER NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
          priority INTEGER NOT NULL DEFAULT 100,
          UNIQUE(user_id, category_id)
        );

        CREATE TABLE IF NOT EXISTS category_income_sources (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          category_id INTEGER NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
          source_id INTEGER NOT NULL REFERENCES income_sources(id) ON DELETE CASCADE,
          percentage REAL NOT NULL,
          UNIQUE(user_id, category_id, source_id)
        );

        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            date TEXT NOT NULL,
            month TEXT NOT NULL,
            category_id INTEGER NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
            amount REAL NOT NULL,
            note TEXT,
            currency TEXT DEFAULT 'RUB'
        );

        CREATE INDEX IF NOT EXISTS idx_expenses_user_date ON expenses(user_id, date DESC);
        CREATE INDEX IF NOT EXISTS idx_expenses_user_month ON expenses(user_id, month);

        CREATE TABLE IF NOT EXISTS password_reset_tokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            token TEXT UNIQUE NOT NULL,
            expires_at DATETIME NOT NULL,
            used INTEGER DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS exchange_rates (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          from_currency TEXT NOT NULL,
          to_currency TEXT NOT NULL,
          rate DECIMAL(10,6) NOT NULL,
          updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
          UNIQUE(from_currency, to_currency)
        );

        CREATE TABLE IF NOT EXISTS budget_rollover (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          category_id INTEGER NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
          month TEXT NOT NULL,
          limit_amount DECIMAL(10,2) NOT NULL DEFAULT 0,
          spent_amount DECIMAL(10,2) NOT NULL DEFAULT 0,
          rollover_amount DECIMAL(10,2) NOT NULL DEFAULT 0,
          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
          updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
          UNIQUE(user_id, category_id, month)
        );
        """
    )
    conn.commit()
    conn.close()

def safe_get_row_value(row, key, default=None):
    try:
        return row[key] if row[key] is not None else default
    except (IndexError, KeyError, TypeError):
        return default

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

def send_reset_email(email, token):
    smtp_server = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
    smtp_port = int(os.environ.get('SMTP_PORT', 587))
    smtp_user = os.environ.get('SMTP_USER')
    smtp_password = os.environ.get('SMTP_PASSWORD')

    if not smtp_user or not smtp_password:
        app.logger.error("SMTP credentials not configured")
        return False

    try:
        reset_link = url_for('reset_password', token=token, _external=True)

        msg = MIMEMultipart()
        msg['From'] = smtp_user
        msg['To'] = email
        msg['Subject'] = "Восстановление пароля - CrystalBudget"

        body = f"""
Здравствуйте!

Вы запросили восстановление пароля для вашего аккаунта в CrystalBudget.

Перейдите по ссылке для создания нового пароля:
{reset_link}

Ссылка действительна в течение 1 часа.

Если вы не запрашивали восстановление пароля, просто проигнорируйте это письмо.

С уважением,
Команда CrystalBudget
"""
        msg.attach(MIMEText(body, 'plain', 'utf-8'))

        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        app.logger.error(f"Failed to send reset email to {email}: {e}")
        return False

def create_reset_token(user_id):
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now() + timedelta(hours=1)
    conn = get_db()
    try:
        conn.execute("DELETE FROM password_reset_tokens WHERE user_id = ?", (user_id,))
        conn.execute(
            "INSERT INTO password_reset_tokens (user_id, token, expires_at) VALUES (?, ?, ?)",
            (user_id, token, expires_at)
        )
        conn.commit()
        return token
    finally:
        conn.close()

# Сессии permanent
@app.before_request
def make_session_permanent():
    session.permanent = True

@app.before_request
def validate_request():
    if request.method == 'POST':
        app.logger.info(f'POST {request.endpoint} from {request.remote_addr}')

# -----------------------------------------------------------------------------
# Routes: favicon and static files
# -----------------------------------------------------------------------------
@app.route('/favicon.ico')
def favicon():
    return redirect(url_for('static', filename='icons/icon-192.png'))

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
    return register_email()

def register_email():
    if request.method == "POST":
        try:
            email = request.form.get("email", "").lower().strip()
            name = request.form.get("name", "").strip()
            password = request.form.get("password", "")

            if not email or not name or not password:
                flash("Все поля обязательны для заполнения", "error")
                return render_template("register.html")

            if len(password) < 6 or ' ' in password:
                flash("Пароль должен быть не короче 6 символов и без пробелов", "error")
                return render_template("register.html")
        except Exception as e:
            app.logger.error(f'Registration form parsing error: {e} - {request.remote_addr}')
            flash("Ошибка обработки формы. Попробуйте еще раз", "error")
            return render_template("register.html")

        conn = get_db()
        try:
            conn.execute(
                "INSERT INTO users(email, name, password_hash, auth_type) VALUES (?,?,?,?)",
                (email, name, generate_password_hash(password), 'email'),
            )
            conn.commit()
            user = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
            if not user:
                raise Exception("Failed to retrieve user after insertion")

            session["user_id"] = user["id"]
            session["email"] = email
            session["name"] = name
            session["theme"] = safe_get_row_value(user, "theme", "light")
            session["currency"] = safe_get_row_value(user, "currency", "RUB")
            session["auth_type"] = "email"
            conn.close()
            return redirect(url_for("dashboard"))
        except sqlite3.IntegrityError:
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
    # Если уже залогинен — на дашборд
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return login_email()

def login_email():
    if request.method == "POST":
        email = (request.form.get("email") or "").lower().strip()
        password = request.form.get("password") or ""

        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE email=? AND auth_type='email'", (email,)).fetchone()
        conn.close()
        if user and check_password_hash(user["password_hash"], password):
            session["user_id"] = user["id"]
            session["email"] = user["email"]
            session["name"] = user["name"]
            session["theme"] = safe_get_row_value(user, "theme", "light")
            session["currency"] = safe_get_row_value(user, "currency", "RUB")
            session["auth_type"] = "email"
            return redirect(url_for("dashboard"))

        flash("Неверный email или пароль", "error")

    # GET или ошибка — показать форму входа с TG-кнопкой
    return render_template("login.html", telegram_bot_username=TELEGRAM_BOT_USERNAME)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/auth/telegram")
def auth_telegram():
    """Авторизация через Telegram Widget"""
    args = request.args
    raw_next = args.get("next") or url_for("dashboard")

    if not BOT_TOKEN:
        app.logger.error('BOT_TOKEN not configured')
        abort(403)

    ok = verify_telegram_auth(args, BOT_TOKEN)
    if not ok:
        app.logger.warning(f'Invalid Telegram auth attempt: {args.get("id")}')
        abort(403)

    tg_id = int(args["id"])
    username = args.get("username")
    first_name = args.get("first_name")
    last_name = args.get("last_name")
    photo_url = args.get("photo_url")

    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE telegram_id = ?", (tg_id,)).fetchone()

    if user is None:
        current_uid = session.get("user_id")
        if current_uid:
            conn.execute("""
                UPDATE users
                   SET telegram_id=?,
                       telegram_username=?,
                       telegram_first_name=?,
                       telegram_last_name=?,
                       telegram_photo_url=?,
                       auth_type=CASE WHEN auth_type='email' THEN 'email' ELSE 'telegram' END
                 WHERE id=?
            """, (tg_id, username, first_name, last_name, photo_url, current_uid))
            conn.commit()
            user = conn.execute("SELECT * FROM users WHERE id=?", (current_uid,)).fetchone()
            flash("Аккаунт Telegram успешно привязан!", "success")
        else:
            display_name = (first_name or "") + ((" " + last_name) if last_name and first_name else (last_name or ""))
            if not display_name.strip():
                display_name = username or f"User{tg_id}"
            fake_email = f"tg{tg_id}@telegram.local"
            fake_pw_hash = generate_password_hash(secrets.token_urlsafe(32))
            conn.execute("""
                INSERT INTO users (email, name, password_hash, auth_type,
                                   telegram_id, telegram_username, telegram_first_name,
                                   telegram_last_name, telegram_photo_url)
                VALUES (?, ?, ?, 'telegram', ?, ?, ?, ?, ?)
            """, (fake_email, display_name, fake_pw_hash,
                  tg_id, username, first_name, last_name, photo_url))
            conn.commit()
            user = conn.execute("SELECT * FROM users WHERE telegram_id=?", (tg_id,)).fetchone()
    else:
        display_name = (first_name or "") + ((" " + last_name) if last_name and first_name else (last_name or ""))
        if not display_name.strip():
            display_name = username or f"User{tg_id}"
        conn.execute("""
            UPDATE users
               SET telegram_username=?,
                   telegram_first_name=?,
                   telegram_last_name=?,
                   telegram_photo_url=?,
                   name=?,
                   auth_type='telegram'
             WHERE id=?
        """, (username, first_name, last_name, photo_url, display_name, user["id"]))
        conn.commit()
        user = conn.execute("SELECT * FROM users WHERE id=?", (user["id"],)).fetchone()

    # Логиним пользователя
    session["user_id"] = user["id"]
    session["email"] = safe_get_row_value(user, "email")
    session["name"] = user["name"]
    session["theme"] = safe_get_row_value(user, "theme", "light")
    session["currency"] = safe_get_row_value(user, "currency", "RUB")
    session["auth_type"] = "telegram"

    conn.close()

    # Безопасно нормализуем next (только внутренние пути, и не /login)
    def _safe_next(u: str) -> str:
        try:
            if not u:
                return url_for("dashboard")
            p = urlparse(u)
            if p.scheme or p.netloc:
                return url_for("dashboard")
            if (p.path or "/") == url_for("login"):
                return url_for("dashboard")
            return u
        except Exception:
            return url_for("dashboard")

    return redirect(_safe_next(raw_next))

# -----------------------------------------------------------------------------
# Forgot / Reset password
# -----------------------------------------------------------------------------
@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = (request.form.get("email") or "").lower().strip()
        if not email:
            flash("Введите email", "error")
            return render_template("forgot_password.html")

        conn = get_db()
        user = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
        conn.close()

        if user:
            token = create_reset_token(user["id"])
            if send_reset_email(email, token):
                flash("Ссылка для восстановления пароля отправлена на ваш email", "success")
            else:
                flash("Ошибка отправки email. Попробуйте позже", "error")
        else:
            flash("Если такой email существует, ссылка для восстановления пароля отправлена", "info")
        return redirect(url_for("login"))
    return render_template("forgot_password.html")

@app.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    conn = get_db()
    try:
        reset_token = conn.execute(
            "SELECT * FROM password_reset_tokens WHERE token = ? AND used = 0 AND expires_at > ?",
            (token, datetime.now())
        ).fetchone()

        if not reset_token:
            flash("Недействительная или истёкшая ссылка", "error")
            return redirect(url_for("login"))

        if request.method == "POST":
            password = (request.form.get("password") or "").strip()
            confirm_password = (request.form.get("confirm_password") or "").strip()
            if not password or len(password) < 6:
                flash("Пароль должен содержать минимум 6 символов", "error")
                return render_template("reset_password.html", token=token)
            if password != confirm_password:
                flash("Пароли не совпадают", "error")
                return render_template("reset_password.html", token=token)

            conn.execute("UPDATE users SET password_hash = ? WHERE id = ?",
                         (generate_password_hash(password), reset_token["user_id"]))
            conn.execute("UPDATE password_reset_tokens SET used = 1 WHERE id = ?",
                         (reset_token["id"],))
            conn.commit()
            flash("Пароль успешно изменён", "success")
            return redirect(url_for("login"))

        return render_template("reset_password.html", token=token)
    finally:
        conn.close()

# -----------------------------------------------------------------------------
# Dashboard & core pages (урезанные версии для краткости ответа)
# -----------------------------------------------------------------------------
@app.route("/dashboard")
@login_required
def dashboard():
    month = request.args.get("month") or datetime.now().strftime("%Y-%m")
    uid = session["user_id"]
    conn = get_db()

    income_sum = conn.execute("""
        SELECT COALESCE(SUM(amount), 0) FROM income_daily
        WHERE user_id = ? AND strftime('%Y-%m', date) = ?
    """, (uid, month)).fetchone()[0]

    categories = conn.execute(
        "SELECT * FROM categories WHERE user_id=? ORDER BY name", (uid,)
    ).fetchall()

    spent_by_cat = conn.execute("""
        SELECT c.id, c.name, COALESCE(SUM(e.amount), 0) as spent
        FROM categories c
        LEFT JOIN expenses e ON e.category_id = c.id AND e.user_id = c.user_id AND e.month = ?
        WHERE c.user_id = ?
        GROUP BY c.id, c.name
    """, (month, uid)).fetchall()

    limits_rows = conn.execute(
        "SELECT id, name, limit_type, value, multi_source FROM categories WHERE user_id=?",
        (uid,),
    ).fetchall()

    # заглушка без многоисточниковости (короткая версия)
    data = []
    for row in limits_rows:
        cat_id = row["id"]
        spent = next((float(s["spent"]) for s in spent_by_cat if s["id"] == cat_id), 0.0)
        limit_val = float(row["value"]) if row["limit_type"] == "fixed" else float(income_sum) * float(row["value"]) / 100.0
        data.append(dict(category_name=row["name"], limit=limit_val, spent=spent, id=cat_id))

    expenses_rows = conn.execute("""
        SELECT e.id, e.date, e.amount, e.note, c.name as category_name
        FROM expenses e JOIN categories c ON e.category_id=c.id
        WHERE e.user_id=? AND e.month=?
        ORDER BY e.date DESC, e.id DESC
    """, (uid, month)).fetchall()

    # упрощённые источники
    sources = conn.execute("SELECT id, name FROM income_sources WHERE user_id=? ORDER BY name", (uid,)).fetchall()
    source_balances = []
    for s in sources:
        inc = conn.execute("SELECT COALESCE(SUM(amount),0) FROM income_daily WHERE user_id=? AND source_id=? AND strftime('%Y-%m',date)=?",
                           (uid, s["id"], month)).fetchone()[0]
        sp = 0.0
        source_balances.append(dict(source_id=s["id"], source_name=s["name"], income=float(inc), spent=float(sp), rest=float(inc)-float(sp),
                                    limits_total=0.0, remaining_after_limits=float(inc)))

    conn.close()

    current_month_name = datetime.strptime(month, "%Y-%m").strftime("%B %Y")
    months_list = generate_months_list(month)
    today = datetime.now().strftime("%Y-%m-%d")

    return render_template(
        "dashboard.html",
        categories=categories,
        expenses=expenses_rows,
        budget_data=data,
        income=income_sum,
        current_month=month,
        current_month_name=current_month_name,
        current_month_human=current_month_name,
        current_ym=month,
        prev_month=None, prev_month_url="#",
        next_month=None, next_month_url="#",
        months=months_list,
        month_names=[],
        today=today,
        source_balances=source_balances,
        sources=sources,
    )

# --- Expenses (упрощённо) ---
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
            flash("Проверьте поля формы", "error")
            return redirect(url_for("expenses"))

        conn = get_db()
        current_currency = session.get('currency', DEFAULT_CURRENCY)
        conn.execute("""
            INSERT INTO expenses (user_id, date, month, category_id, amount, note, currency)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (uid, date_str, date_str[:7], int(category_id), amount, note, current_currency))
        conn.commit()
        conn.close()
        flash("Расход добавлен", "success")
        return redirect(url_for("expenses"))

    conn = get_db()
    cats = conn.execute("SELECT id, name FROM categories WHERE user_id=? ORDER BY name", (uid,)).fetchall()
    rows = conn.execute("""
        SELECT e.id, e.date, e.amount, e.note, e.currency, c.name AS category_name
        FROM expenses e JOIN categories c ON c.id=e.category_id
        WHERE e.user_id=? ORDER BY e.date DESC, e.id DESC
    """, (uid,)).fetchall()
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

# --- Income (упрощённо) ---
@app.route("/income")
@login_required
def income_page():
    uid = session["user_id"]
    conn = get_db()
    rows = conn.execute("""
        SELECT id, date, amount, source_id, currency
        FROM income_daily WHERE user_id=? ORDER BY date DESC, id DESC
    """, (uid,)).fetchall()
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
    current_currency = session.get('currency', DEFAULT_CURRENCY)
    conn.execute(
        "INSERT INTO income_daily (user_id, date, amount, source_id, currency) VALUES (?,?,?,?,?)",
        (uid, date_str, amount, source_id, current_currency),
    )
    conn.commit()
    conn.close()
    flash("Доход добавлен", "success")
    return redirect(url_for("income_page"))

# -----------------------------------------------------------------------------
# Templates (включая обновлённый логин с TG-виджетом)
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
    .form-control { padding-top: .5rem; padding-bottom: .5rem; } /* компактнее */
    .btn { padding-top: .5rem; padding-bottom: .5rem; }           /* компактнее */
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
          <a class="btn btn_sm btn-outline-light" href="{{ url_for('expenses') }}">Траты</a>
          <a class="btn btn_sm btn-outline-light" href="{{ url_for('income_page') }}">Доходы</a>
          <a class="btn btn_sm btn-warning" href="{{ url_for('logout') }}">Выйти</a>
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
</body>
</html>
"""

LOGIN_HTML = """
{% extends "base.html" %}
{% block title %}Вход — CrystalBudget{% endblock %}
{% block content %}
<div class="mx-auto" style="max-width:420px;">
  <h3 class="mb-2 text-center">Вход</h3>
  <p class="text-muted text-center mb-3">Выберите способ авторизации</p>

  <!-- Telegram Login -->
  <div class="text-center mb-2">
    <script async src="https://telegram.org/js/telegram-widget.js?22"
      data-telegram-login="{{ telegram_bot_username }}"
      data-size="large"
      data-userpic="false"
      data-request-access="write"
      data-auth-url="{{ url_for('auth_telegram', _external=True, next=request.args.get('next', url_for('dashboard'))) }}">
    </script>
  </div>

  <div class="text-center text-muted small mb-3">или</div>

  <!-- Email Login -->
  <form method="post" class="mb-2">
    <div class="mb-2">
      <label class="form-label">Email</label>
      <input class="form-control" type="email" name="email" required>
    </div>
    <div class="mb-3">
      <label class="form-label">Пароль</label>
      <input class="form-control" type="password" name="password" required>
    </div>
    <button class="btn btn-primary w-100">Войти</button>
  </form>

  <div class="text-center mb-2">
    <a href="{{ url_for('forgot_password') }}" class="small">Забыли пароль?</a>
  </div>
  <div class="text-center">
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
    <div class="mb-2"><label class="form-label">Имя</label><input class="form-control" name="name" required></div>
    <div class="mb-2"><label class="form-label">Email</label><input class="form-control" type="email" name="email" required></div>
    <div class="mb-2"><label class="form-label">Пароль</label><input class="form-control" type="password" name="password" required></div>
    <div class="mb-3"><label class="form-label">Повторите пароль</label><input class="form-control" type="password" name="confirm" required></div>
    <button class="btn btn-success w-100">Создать аккаунт</button>
  </form>
  <div class="text-center mt-2"><a href="{{ url_for('login') }}">У меня уже есть аккаунт</a></div>
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
        <div class="d-flex justify-content-between"><span>Пришло</span><strong>{{ s.income|format_amount }} {{ currency_symbol }}</strong></div>
        <div class="d-flex justify-content-between"><span>Ушло</span><strong>{{ s.spent|format_amount }} {{ currency_symbol }}</strong></div>
        <div class="d-flex justify-content-between"><span>Остаток</span><strong>{{ s.rest|format_amount }} {{ currency_symbol }}</strong></div>
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
            Лимит: {{ item.limit|format_amount }} {{ currency_symbol }} •
            Потрачено: {{ item.spent|format_amount }} {{ currency_symbol }}
          </div>
        </div>
      </div>
      {% endfor %}
    </div>
  </div>
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
        <td class="text-end fw-semibold">{{ e.amount|format_amount }} {{ currency_symbol }}</td>
        <td>{{ e.note or '' }}</td>
        <td class="text-end">
          <form method="POST" action="{{ url_for('delete_expense', expense_id=e.id) }}" class="d-inline">
            <button class="btn btn-sm btn-outline-danger" onclick="return confirm('Удалить расход?')">Удалить</button>
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
      <div class="col-md-3"><label class="form-label">Дата</label><input class="form-control" type="date" name="date" value="{{ today }}" required></div>
      <div class="col-md-3"><label class="form-label">Сумма</label><input class="form-control" type="number" name="amount" step="0.01" min="0.01" required></div>
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
        <td class="text-end fw-semibold">{{ i.amount|format_amount }} {{ currency_symbol }}</td>
        <td>
          {% if i.source_id %}
            {% set nm = (income_sources | selectattr('id','equalto', i.source_id) | list) %}
            {{ nm[0].name if nm and nm[0] else '—' }}
          {% else %}—{% endif %}
        </td>
        <td class="text-end">
          <form class="d-inline" method="POST" action="{{ url_for('delete_income', income_id=i.id) }}"><button class="btn btn-sm btn-outline-danger" onclick="return confirm('Удалить доход?')">Удалить</button></form>
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
        app.jinja_loader,
        DictLoader({
            "base.html": BASE_HTML,
            "login.html": LOGIN_HTML,
            "register.html": REGISTER_HTML,
            "dashboard.html": DASHBOARD_HTML,
            "expenses.html": EXPENSES_HTML,
            "income.html": INCOME_HTML,
        }),
    ]
)

# -----------------------------------------------------------------------------
# Security headers
# -----------------------------------------------------------------------------
@app.after_request
def set_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    csp_base = [
        "default-src 'self'",
        "script-src 'self' 'unsafe-inline' https://telegram.org",
        "style-src 'self' 'unsafe-inline'",
        "font-src 'self' data:",
        "img-src 'self' data:",
        "connect-src 'self' https://api.exchangerate.host",
        "frame-src https://oauth.telegram.org"
    ]
    response.headers['Content-Security-Policy'] = "; ".join(csp_base)
    if os.environ.get('HTTPS_MODE', 'false').lower() == 'true':
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    if request.endpoint == 'static':
        response.headers['Cache-Control'] = 'public, max-age=86400'
    return response

# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=os.environ.get("FLASK_ENV") == "development")
