import os
import sqlite3
from datetime import datetime, date
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from flask import Flask, render_template, request, redirect, url_for, flash, session
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

# Templates are now loaded from templates/ directory using Flask's default template loader

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
    """Create default categories for new user - disabled"""
    # No default categories - users create their own
    return 0

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
    
    # Get income for month - FIXED: added user_id filter
    cursor = conn.execute('SELECT amount FROM income WHERE month = ? AND user_id = ?', (month, user_id))
    income_row = cursor.fetchone()
    income = float(income_row['amount']) if income_row else 0.0
    
    # Get total expenses for month - FIXED: added user_id filter
    cursor = conn.execute('''
        SELECT COALESCE(SUM(amount), 0) as total_expenses
        FROM expenses 
        WHERE month = ? AND user_id = ?
    ''', (month, user_id))
    expenses = float(cursor.fetchone()['total_expenses'])
    
    # Get categories and calculate budget data - FIXED: added user_id filter
    cursor = conn.execute('SELECT * FROM categories WHERE user_id = ? ORDER BY name', (user_id,))
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
        
        # Calculate spent this month - FIXED: added user_id filter
        cursor = conn.execute('''
            SELECT COALESCE(SUM(amount), 0) as spent
            FROM expenses 
            WHERE category_id = ? AND month = ? AND user_id = ?
        ''', (category['id'], month, user_id))
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
            
            # Validation
            if not all([name, email, password]):
                flash('Пожалуйста, заполните все поля', 'error')
                return render_template('register.html')
            
            if len(name) < 2:
                flash('Имя должно содержать минимум 2 символа', 'error')
                return render_template('register.html')
                
            if len(password) < 6:
                flash('Пароль должен содержать минимум 6 символов', 'error')
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
            
            flash(f'Добро пожаловать в CrystalBudget, {name}!', 'success')
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

@app.route('/add-expense', methods=['POST'])
@login_required
def add_expense_quick():
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

@app.route('/expenses/edit/<int:expense_id>', methods=['GET', 'POST'])
@login_required
def edit_expense(expense_id):
    user_id = session['user_id']
    
    if request.method == 'GET':
        # Get expense data
        def get_expense_op(conn, user_id, expense_id):
            cursor = conn.execute('''
                SELECT e.*, c.name as category_name
                FROM expenses e
                JOIN categories c ON e.category_id = c.id
                WHERE e.id = ? AND e.user_id = ?
            ''', (expense_id, user_id))
            return cursor.fetchone()
        
        expense = safe_db_operation(get_expense_op, user_id, expense_id)
        
        if not expense:
            flash('Трата не найдена', 'error')
            return redirect(url_for('expenses'))
        
        # Get categories for dropdown
        def get_categories_op(conn, user_id):
            cursor = conn.execute('SELECT * FROM categories WHERE user_id = ? ORDER BY name', (user_id,))
            return cursor.fetchall()
        
        categories = safe_db_operation(get_categories_op, user_id)
        
        return render_template('edit_expense.html', expense=expense, categories=categories)
    
    else:  # POST
        try:
            date_str = request.form.get('date', '').strip()
            category_id = request.form.get('category_id', '').strip()
            amount_str = request.form.get('amount', '').strip()
            note = escape(request.form.get('note', '').strip())
            
            if not date_str or not category_id or not amount_str:
                flash('Ошибка: все обязательные поля должны быть заполнены', 'error')
                return redirect(url_for('edit_expense', expense_id=expense_id))
            
            validated_date = validate_date(date_str)
            amount = validate_amount(amount_str)
            month = validated_date.strftime('%Y-%m')
            
            def update_expense_op(conn, user_id, expense_id, date_str, month, category_id, amount, note):
                cursor = conn.execute('''
                    UPDATE expenses 
                    SET date = ?, month = ?, category_id = ?, amount = ?, note = ?
                    WHERE id = ? AND user_id = ?
                ''', (date_str, month, int(category_id), float(amount), note, expense_id, user_id))
                return cursor.rowcount
            
            result = safe_db_operation(update_expense_op, user_id, expense_id, date_str, month, category_id, amount, note)
            
            if result > 0:
                flash(f'✓ Трата обновлена: {amount} руб.', 'success')
            else:
                flash('Трата не найдена', 'error')
            
            return redirect(url_for('expenses'))
            
        except ValueError as e:
            flash(f'Ошибка: {str(e)}', 'error')
            return redirect(url_for('edit_expense', expense_id=expense_id))
        except Exception as e:
            flash(f'Неожиданная ошибка: {str(e)}', 'error')
            return redirect(url_for('edit_expense', expense_id=expense_id))

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
    
    return render_template("categories.html", categories=categories_list)

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
    
    return render_template("income.html", incomes=incomes, current_month=current_month)

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

@app.route('/income/edit/<string:month>', methods=['GET', 'POST'])
@login_required
def edit_income(month):
    user_id = session['user_id']
    
    if request.method == 'GET':
        # Get income data
        def get_income_op(conn, user_id, month):
            cursor = conn.execute('SELECT * FROM income WHERE user_id = ? AND month = ?', (user_id, month))
            return cursor.fetchone()
        
        income_data = safe_db_operation(get_income_op, user_id, month)
        
        if not income_data:
            flash('Доход не найден', 'error')
            return redirect(url_for('income'))
        
        return render_template('edit_income.html', income=income_data)
    
    else:  # POST
        try:
            new_month = request.form.get('month', '').strip()
            amount_str = request.form.get('amount', '').strip()
            
            if not new_month or not amount_str:
                flash('Пожалуйста, заполните все поля', 'error')
                return redirect(url_for('edit_income', month=month))
            
            # Validate month format
            try:
                datetime.strptime(new_month, '%Y-%m')
            except ValueError:
                flash('Некорректный формат месяца', 'error')
                return redirect(url_for('edit_income', month=month))
                
            amount = validate_amount(amount_str)
            
            def update_income_op(conn, user_id, old_month, new_month, amount):
                if old_month != new_month:
                    # Delete old record and insert new one
                    conn.execute('DELETE FROM income WHERE user_id = ? AND month = ?', (user_id, old_month))
                    cursor = conn.execute(
                        'INSERT INTO income (user_id, month, amount) VALUES (?, ?, ?)',
                        (user_id, new_month, float(amount))
                    )
                else:
                    # Update existing record
                    cursor = conn.execute(
                        'UPDATE income SET amount = ? WHERE user_id = ? AND month = ?',
                        (float(amount), user_id, old_month)
                    )
                return cursor.rowcount
            
            result = safe_db_operation(update_income_op, user_id, month, new_month, amount)
            
            if result > 0:
                flash(f'✓ Доход за {new_month} обновлен: {amount} руб.', 'success')
            else:
                flash('Доход не найден', 'error')
            
            return redirect(url_for('income'))
            
        except ValueError as e:
            flash(f'Ошибка: {str(e)}', 'error')
            return redirect(url_for('edit_income', month=month))
        except Exception as e:
            flash(f'Неожиданная ошибка: {str(e)}', 'error')
            return redirect(url_for('edit_income', month=month))

@app.route('/income/delete/<string:month>', methods=['POST'])
@login_required
def delete_income(month):
    try:
        user_id = session['user_id']
        
        def delete_income_op(conn, user_id, month):
            cursor = conn.execute('DELETE FROM income WHERE user_id = ? AND month = ?', (user_id, month))
            return cursor.rowcount
        
        result = safe_db_operation(delete_income_op, user_id, month)
        
        if result > 0:
            flash(f'✓ Доход за {month} удален!', 'success')
        else:
            flash('Доход не найден', 'error')
            
    except Exception as e:
        flash(f'Ошибка при удалении: {str(e)}', 'error')
    
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