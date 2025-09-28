"""CLI commands for the application."""
import click
from flask import current_app
from flask.cli import with_appcontext
from app.core.extensions import db
from app.modules.auth.models import User
from app.modules.budget.models import Category
from app.modules.budget.service import BudgetService
from app.core.time import YearMonth
from decimal import Decimal


@click.group()
def budget_cli():
    """Budget management commands."""
    pass


@budget_cli.command()
@click.option('--user-id', type=int, required=True, help='User ID')
@click.option('--ym', help='Year-Month (YYYY-MM), defaults to current')
@with_appcontext
def recalc_month(user_id, ym):
    """Recalculate budget snapshot for user and month."""
    try:
        from app.core.time import parse_year_month
        year_month = parse_year_month(ym) if ym else YearMonth.current()
        
        # Check if user exists
        user = User.query.get(user_id)
        if not user:
            click.echo(f"Error: User {user_id} not found")
            return
        
        # Calculate snapshot
        snapshot = BudgetService.calculate_month_snapshot(user_id, year_month)
        
        click.echo(f"✓ Recalculated budget for user {user_id} ({user.name}) for {year_month}")
        click.echo(f"  Total income: {snapshot['total_income'].format()}")
        click.echo(f"  Total spent: {snapshot['total_spent'].format()}")
        click.echo(f"  Remaining: {snapshot['total_remaining'].format()}")
        click.echo(f"  Categories: {len(snapshot['categories'])}")
        
    except Exception as e:
        click.echo(f"Error: {e}")


@budget_cli.command()
@click.option('--user-id', type=int, required=True, help='User ID')
@with_appcontext
def sync_currencies(user_id):
    """Sync currency exchange rates (placeholder)."""
    click.echo(f"Syncing currencies for user {user_id}...")
    # TODO: Implement actual currency sync
    click.echo("✓ Currency sync completed (placeholder)")


@budget_cli.command()
@click.option('--user-id', type=int, required=True, help='User ID')
@click.option('--from-month', help='From month (YYYY-MM)')
@click.option('--to-month', help='To month (YYYY-MM)')
@with_appcontext
def process_carryovers(user_id, from_month, to_month):
    """Process carryovers from one month to another."""
    try:
        from app.core.time import parse_year_month
        
        # Check if user exists
        user = User.query.get(user_id)
        if not user:
            click.echo(f"Error: User {user_id} not found")
            return
        
        # Parse months
        if from_month:
            from_ym = parse_year_month(from_month)
        else:
            from_ym = YearMonth.current().prev_month()
            
        if to_month:
            to_ym = parse_year_month(to_month)
        else:
            to_ym = YearMonth.current()
        
        # Process carryovers
        BudgetService.process_month_carryovers(user_id, from_ym, to_ym)
        
        click.echo(f"✓ Processed carryovers for user {user_id} ({user.name})")
        click.echo(f"  From: {from_ym}")
        click.echo(f"  To: {to_ym}")
        
        # Show summary of carryovers created
        categories = BudgetService.get_user_categories(user_id)
        carryover_count = 0
        total_carryover = Decimal('0')
        
        for category in categories:
            carryover_info = BudgetService.get_category_carryover_info(user_id, category.id, to_ym)
            if carryover_info['has_carryover']:
                carryover_count += 1
                total_carryover += abs(carryover_info['amount'])
                click.echo(f"  {category.name}: {carryover_info['amount']} ₽")
        
        click.echo(f"Total categories with carryovers: {carryover_count}")
        
    except Exception as e:
        click.echo(f"Error: {e}")


@click.group()
def user_cli():
    """User management commands."""
    pass


@user_cli.command()
@with_appcontext
def list_users():
    """List all users."""
    users = User.query.all()
    
    if not users:
        click.echo("No users found")
        return
    
    click.echo(f"Found {len(users)} users:")
    click.echo("-" * 60)
    
    for user in users:
        click.echo(f"ID: {user.id}")
        click.echo(f"Name: {user.name}")
        click.echo(f"Email: {user.email}")
        click.echo(f"Auth Type: {user.auth_type}")
        if user.is_telegram_user:
            click.echo(f"Telegram ID: {user.telegram_id}")
        click.echo(f"Created: {user.created_at}")
        click.echo("-" * 60)


@user_cli.command()
@click.option('--user-id', type=int, required=True, help='User ID')
@with_appcontext
def user_stats(user_id):
    """Show user statistics."""
    user = User.query.get(user_id)
    if not user:
        click.echo(f"Error: User {user_id} not found")
        return
    
    # Get categories count
    categories = BudgetService.get_user_categories(user_id)
    
    # Get current month snapshot
    current_month = YearMonth.current()
    snapshot = BudgetService.calculate_month_snapshot(user_id, current_month)
    
    click.echo(f"User Statistics for {user.name} (ID: {user_id})")
    click.echo("=" * 50)
    click.echo(f"Email: {user.email}")
    click.echo(f"Auth Type: {user.auth_type}")
    click.echo(f"Theme: {user.theme}")
    click.echo(f"Currency: {user.currency}")
    click.echo(f"Created: {user.created_at}")
    click.echo()
    click.echo("Budget Statistics:")
    click.echo(f"  Categories: {len(categories)}")
    click.echo(f"  Current month income: {snapshot['total_income'].format()}")
    click.echo(f"  Current month spent: {snapshot['total_spent'].format()}")
    click.echo(f"  Current month remaining: {snapshot['total_remaining'].format()}")
    click.echo(f"  Expenses this month: {len(snapshot['expenses'])}")


@user_cli.command()
@click.option('--name', required=True, help='User name')
@click.option('--email', required=True, help='User email')
@click.option('--password', required=True, help='User password')
@with_appcontext
def create_user(name, email, password):
    """Create a new email user."""
    from app.modules.auth.service import AuthService
    
    # Check if user exists
    existing_user = User.query.filter_by(email=email).first()
    if existing_user:
        click.echo(f"Error: User with email {email} already exists")
        return
    
    try:
        user = AuthService.register_email(
            email=email,
            name=name,
            password=password
        )
        if user:
            click.echo(f"✓ Created user: {user.name} (ID: {user.id})")
            click.echo(f"  Email: {user.email}")
            click.echo(f"  Auth Type: {user.auth_type}")
        else:
            click.echo("Error: Failed to create user")
        
    except Exception as e:
        click.echo(f"Error creating user: {e}")


@click.group()
def db_cli():
    """Database management commands."""
    pass


@db_cli.command()
@click.option('--user-id', type=int, required=True, help='User ID')
@with_appcontext
def seed_categories(user_id):
    """Seed default categories for user."""
    user = User.query.get(user_id)
    if not user:
        click.echo(f"Error: User {user_id} not found")
        return
    
    # Check if user already has categories
    existing_categories = BudgetService.get_user_categories(user_id)
    if existing_categories:
        click.echo(f"User {user_id} already has {len(existing_categories)} categories")
        if not click.confirm("Do you want to add default categories anyway?"):
            return
    
    # Default categories
    default_categories = [
        ("Продукты", "percent", 30.0),
        ("Транспорт", "fixed", 5000.0),
        ("Развлечения", "percent", 15.0),
        ("Коммунальные", "fixed", 8000.0),
        ("Здоровье", "fixed", 3000.0),
        ("Одежда", "percent", 10.0),
    ]
    
    created_count = 0
    for name, limit_type, value in default_categories:
        try:
            BudgetService.create_category(
                user_id=user_id,
                name=name,
                limit_type=limit_type,
                value=Decimal(str(value))
            )
            created_count += 1
            click.echo(f"✓ Created category: {name}")
        except Exception as e:
            click.echo(f"✗ Failed to create category {name}: {e}")
    
    click.echo(f"Created {created_count} categories for user {user_id}")


@db_cli.command()
@with_appcontext
def init_db():
    """Initialize database with tables and handle schema migrations."""
    try:
        # Import all models to ensure they're registered
        from app.modules.auth.models import User
        from app.modules.budget.models import Category, Expense, Income, ExchangeRate, IncomeSource, CategoryRule
        from app.modules.goals.models import SavingsGoal, SharedBudget, SharedBudgetMember
        from app.modules.issues.models import Issue, IssueComment
        
        # Create all tables first
        db.create_all()
        click.echo("✓ All tables created/updated")
        
        # Handle potential schema updates for production data
        from sqlalchemy import text
        connection = db.engine.connect()
        missing_columns = []
        added_tables = []
        
        # Check for missing tables that might not be created by SQLAlchemy
        try:
            # Check if planned_income table exists
            result = connection.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='planned_income'"))
            if not result.fetchone():
                connection.execute(text("""
                    CREATE TABLE planned_income (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                        year INTEGER NOT NULL,
                        month INTEGER NOT NULL,
                        source_id INTEGER REFERENCES income_sources(id) ON DELETE CASCADE,
                        amount REAL NOT NULL,
                        UNIQUE(user_id, year, month, source_id)
                    )
                """))
                connection.execute(text("CREATE INDEX idx_planned_income_user_period ON planned_income(user_id, year, month)"))
                added_tables.append("planned_income")
        except Exception as e:
            click.echo(f"Note: Could not create planned_income table: {e}")
        
        try:
            # Check if operation_log table exists
            result = connection.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='operation_log'"))
            if not result.fetchone():
                connection.execute(text("""
                    CREATE TABLE operation_log (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                        operation_id TEXT NOT NULL,
                        resource_id INTEGER,
                        kind TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(user_id, operation_id)
                    )
                """))
                added_tables.append("operation_log")
        except Exception as e:
            click.echo(f"Note: Could not create operation_log table: {e}")
        
        try:
            # Check if budget_rollover table exists with correct schema
            result = connection.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='budget_rollover'"))
            if not result.fetchone():
                connection.execute(text("""
                    CREATE TABLE budget_rollover (
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
                    )
                """))
                added_tables.append("budget_rollover")
        except Exception as e:
            click.echo(f"Note: Could not create budget_rollover table: {e}")
        
        try:
            # Check if income_backup_monthly has correct schema
            result = connection.execute(text("PRAGMA table_info(income_backup_monthly)"))
            columns = [row[1] for row in result.fetchall()]
            if 'id' not in columns:
                # Recreate table with proper schema
                connection.execute(text("DROP TABLE IF EXISTS income_backup_monthly"))
                connection.execute(text("""
                    CREATE TABLE income_backup_monthly (
                        id INTEGER NOT NULL, 
                        user_id INTEGER NOT NULL, 
                        source_name VARCHAR(100) NOT NULL, 
                        amount NUMERIC(10, 2) NOT NULL, 
                        currency VARCHAR(3), 
                        year INTEGER NOT NULL, 
                        month INTEGER NOT NULL, 
                        created_at DATETIME, 
                        PRIMARY KEY (id), 
                        FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
                        UNIQUE (user_id, source_name, year, month)
                    )
                """))
                added_tables.append("income_backup_monthly (recreated)")
        except Exception as e:
            click.echo(f"Note: Could not fix income_backup_monthly table: {e}")
        
        # Check and add missing columns with proper error handling
        try:
            # Check for date column in income table (new field)
            result = connection.execute(text("PRAGMA table_info(income)"))
            columns = [row[1] for row in result.fetchall()]
            if 'date' not in columns:
                connection.execute(text("ALTER TABLE income ADD COLUMN date DATE"))
                missing_columns.append("income.date")
            if 'source_name' not in columns:
                connection.execute(text("ALTER TABLE income ADD COLUMN source_name TEXT NOT NULL DEFAULT 'Основной'"))
                missing_columns.append("income.source_name")
            if 'year' not in columns:
                connection.execute(text("ALTER TABLE income ADD COLUMN year INTEGER"))
                missing_columns.append("income.year")
            if 'created_at' not in columns:
                connection.execute(text("ALTER TABLE income ADD COLUMN created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP"))
                missing_columns.append("income.created_at")
        except Exception as e:
            click.echo(f"Note: Could not add income columns: {e}")
        
        try:
            # Check for currency column in various tables
            for table in ['expenses', 'income']:
                result = connection.execute(text(f"PRAGMA table_info({table})"))
                columns = [row[1] for row in result.fetchall()]
                if 'currency' not in columns:
                    connection.execute(text(f"ALTER TABLE {table} ADD COLUMN currency VARCHAR(3) DEFAULT 'RUB'"))
                    missing_columns.append(f"{table}.currency")
        except Exception as e:
            click.echo(f"Note: Could not add currency columns: {e}")
        
        try:
            # Check for theme column in users table
            result = connection.execute(text("PRAGMA table_info(users)"))
            columns = [row[1] for row in result.fetchall()]
            if 'theme' not in columns:
                connection.execute(text("ALTER TABLE users ADD COLUMN theme VARCHAR(10) DEFAULT 'light'"))
                missing_columns.append("users.theme")
        except Exception as e:
            click.echo(f"Note: Could not add users.theme column: {e}")
        
        try:
            # Check for auth_type and telegram_id columns in users table
            result = connection.execute(text("PRAGMA table_info(users)"))
            columns = [row[1] for row in result.fetchall()]
            if 'auth_type' not in columns:
                connection.execute(text("ALTER TABLE users ADD COLUMN auth_type VARCHAR(20) DEFAULT 'email'"))
                missing_columns.append("users.auth_type")
            if 'telegram_id' not in columns:
                connection.execute(text("ALTER TABLE users ADD COLUMN telegram_id BIGINT"))
                missing_columns.append("users.telegram_id")
            if 'telegram_username' not in columns:
                connection.execute(text("ALTER TABLE users ADD COLUMN telegram_username VARCHAR(100)"))
                missing_columns.append("users.telegram_username")
            if 'telegram_first_name' not in columns:
                connection.execute(text("ALTER TABLE users ADD COLUMN telegram_first_name VARCHAR(100)"))
                missing_columns.append("users.telegram_first_name")
            if 'telegram_last_name' not in columns:
                connection.execute(text("ALTER TABLE users ADD COLUMN telegram_last_name VARCHAR(100)"))
                missing_columns.append("users.telegram_last_name")
            if 'telegram_photo_url' not in columns:
                connection.execute(text("ALTER TABLE users ADD COLUMN telegram_photo_url VARCHAR(500)"))
                missing_columns.append("users.telegram_photo_url")
        except Exception as e:
            click.echo(f"Note: Could not add users auth columns: {e}")
        
        try:
            # Check for rollover_from_previous column in categories
            result = connection.execute(text("PRAGMA table_info(categories)"))
            columns = [row[1] for row in result.fetchall()]
            if 'rollover_from_previous' not in columns:
                connection.execute(text("ALTER TABLE categories ADD COLUMN rollover_from_previous DECIMAL(10,2) DEFAULT 0"))
                missing_columns.append("categories.rollover_from_previous")
            if 'is_multi_source' not in columns:
                connection.execute(text("ALTER TABLE categories ADD COLUMN is_multi_source BOOLEAN DEFAULT 0"))
                missing_columns.append("categories.is_multi_source")
        except Exception as e:
            click.echo(f"Note: Could not add categories columns: {e}")
        
        try:
            # Check for description column in expenses
            result = connection.execute(text("PRAGMA table_info(expenses)"))
            columns = [row[1] for row in result.fetchall()]
            if 'description' not in columns:
                connection.execute(text("ALTER TABLE expenses ADD COLUMN description TEXT"))
                missing_columns.append("expenses.description")
        except Exception as e:
            click.echo(f"Note: Could not add expenses.description column: {e}")
        
        # Create missing indices
        try:
            connection.execute(text("CREATE INDEX IF NOT EXISTS idx_expenses_user_date ON expenses(user_id, date DESC)"))
            connection.execute(text("CREATE INDEX IF NOT EXISTS idx_expenses_user_month ON expenses(user_id, month)"))
            connection.execute(text("CREATE INDEX IF NOT EXISTS idx_expenses_category ON expenses(category_id)"))
            connection.execute(text("CREATE INDEX IF NOT EXISTS idx_categories_user ON categories(user_id)"))
            connection.execute(text("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)"))
            connection.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_telegram_id ON users(telegram_id) WHERE telegram_id IS NOT NULL"))
        except Exception as e:
            click.echo(f"Note: Could not create indices: {e}")
        
        connection.close()
        
        if added_tables:
            click.echo(f"✓ Added missing tables: {', '.join(added_tables)}")
        if missing_columns:
            click.echo(f"✓ Added missing columns: {', '.join(missing_columns)}")
        if not added_tables and not missing_columns:
            click.echo("✓ All tables and columns up to date")
            
        click.echo("✓ Database initialization completed successfully")
        
    except Exception as e:
        click.echo(f"Error initializing database: {e}")
        raise


@click.group()
def dev_cli():
    """Development commands."""
    pass


@dev_cli.command()
@click.option('--user-id', type=int, required=True, help='User ID')
@click.option('--count', type=int, default=10, help='Number of expenses to create')
@with_appcontext
def create_test_expenses(user_id, count):
    """Create test expenses for development."""
    import random
    from datetime import datetime, timedelta
    
    user = User.query.get(user_id)
    if not user:
        click.echo(f"Error: User {user_id} not found")
        return
    
    categories = BudgetService.get_user_categories(user_id)
    if not categories:
        click.echo(f"User {user_id} has no categories. Create some first.")
        return
    
    created_count = 0
    for i in range(count):
        try:
            # Random category
            category = random.choice(categories)
            
            # Random amount between 100 and 5000
            amount = Decimal(str(random.randint(100, 5000)))
            
            # Random date within last 30 days
            days_ago = random.randint(0, 30)
            date_val = (datetime.now() - timedelta(days=days_ago)).date()
            
            # Random description
            descriptions = [
                "Тестовый расход",
                "Покупка в магазине",
                "Оплата услуг",
                "Развлечения",
                "Транспорт"
            ]
            description = random.choice(descriptions)
            
            BudgetService.add_expense(
                user_id=user_id,
                category_id=category.id,
                amount=amount,
                description=description,
                date_val=date_val
            )
            created_count += 1
            
        except Exception as e:
            click.echo(f"✗ Failed to create expense {i+1}: {e}")
    
    click.echo(f"Created {created_count} test expenses for user {user_id}")


def register_cli_commands(app):
    """Register CLI commands with the app."""
    app.cli.add_command(budget_cli)
    app.cli.add_command(user_cli)
    app.cli.add_command(db_cli)
    app.cli.add_command(dev_cli)
    
    # Register screenshot commands
    from app.core.screenshot_cli import register_screenshot_commands
    register_screenshot_commands(app)