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
    """Initialize database with tables."""
    try:
        db.create_all()
        click.echo("✓ Database initialized successfully")
    except Exception as e:
        click.echo(f"Error initializing database: {e}")


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