"""Sync all tables with current schema

Revision ID: sync_all_tables_schema
Revises: sync_all_expenses_columns
Create Date: 2025-10-04 00:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

# revision identifiers, used by Alembic.
revision = 'sync_all_tables_schema'
down_revision = 'sync_all_expenses_columns'
branch_labels = None
depends_on = None


def upgrade():
    """Ensure all tables have required columns."""
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)

    # ========== CATEGORIES TABLE ==========
    print("\n=== Syncing categories table ===")
    if 'categories' in inspector.get_table_names():
        columns = {col['name']: col for col in inspector.get_columns('categories')}
        print(f"Current columns: {list(columns.keys())}")

        missing_columns = []

        if 'shared_budget_id' not in columns:
            missing_columns.append(('shared_budget_id', sa.Integer, True))

        if 'created_at' not in columns:
            missing_columns.append(('created_at', sa.DateTime, True))

        if 'is_multi_source' not in columns:
            missing_columns.append(('is_multi_source', sa.Boolean, True))

        if missing_columns:
            with op.batch_alter_table('categories', schema=None) as batch_op:
                for col_name, col_type, nullable in missing_columns:
                    batch_op.add_column(sa.Column(col_name, col_type, nullable=nullable))
                    print(f"✓ Added '{col_name}' to categories")

            # Set defaults
            if 'is_multi_source' in [c[0] for c in missing_columns]:
                conn.execute(sa.text("UPDATE categories SET is_multi_source = 0 WHERE is_multi_source IS NULL"))

    # ========== USERS TABLE ==========
    print("\n=== Syncing users table ===")
    if 'users' in inspector.get_table_names():
        columns = {col['name']: col for col in inspector.get_columns('users')}
        print(f"Current columns: {list(columns.keys())}")

        missing_columns = []

        if 'shared_budget_id' not in columns:
            missing_columns.append(('shared_budget_id', sa.Integer, True))

        if 'theme' not in columns:
            missing_columns.append(('theme', sa.String(20), True))

        if 'currency' not in columns:
            missing_columns.append(('currency', sa.String(3), True))

        if 'timezone' not in columns:
            missing_columns.append(('timezone', sa.String(50), True))

        if 'locale' not in columns:
            missing_columns.append(('locale', sa.String(10), True))

        if 'default_currency' not in columns:
            missing_columns.append(('default_currency', sa.String(3), True))

        if 'telegram_id' not in columns:
            missing_columns.append(('telegram_id', sa.BigInteger, True))

        if 'telegram_username' not in columns:
            missing_columns.append(('telegram_username', sa.String(100), True))

        if 'telegram_first_name' not in columns:
            missing_columns.append(('telegram_first_name', sa.String(100), True))

        if 'telegram_last_name' not in columns:
            missing_columns.append(('telegram_last_name', sa.String(100), True))

        if 'telegram_photo_url' not in columns:
            missing_columns.append(('telegram_photo_url', sa.String(500), True))

        if 'auth_type' not in columns:
            missing_columns.append(('auth_type', sa.String(20), True))

        if missing_columns:
            with op.batch_alter_table('users', schema=None) as batch_op:
                for col_name, col_type, nullable in missing_columns:
                    batch_op.add_column(sa.Column(col_name, col_type, nullable=nullable))
                    print(f"✓ Added '{col_name}' to users")

            # Set defaults
            if 'auth_type' in [c[0] for c in missing_columns]:
                conn.execute(sa.text("UPDATE users SET auth_type = 'email' WHERE auth_type IS NULL"))

            if 'default_currency' in [c[0] for c in missing_columns]:
                conn.execute(sa.text("UPDATE users SET default_currency = 'RUB' WHERE default_currency IS NULL"))

    # ========== INCOME TABLE ==========
    print("\n=== Syncing income table ===")
    if 'income' in inspector.get_table_names():
        columns = {col['name']: col for col in inspector.get_columns('income')}
        print(f"Current columns: {list(columns.keys())}")

        missing_columns = []

        if 'date' not in columns:
            missing_columns.append(('date', sa.Date, True))

        if 'created_at' not in columns:
            missing_columns.append(('created_at', sa.DateTime, True))

        if missing_columns:
            with op.batch_alter_table('income', schema=None) as batch_op:
                for col_name, col_type, nullable in missing_columns:
                    batch_op.add_column(sa.Column(col_name, col_type, nullable=nullable))
                    print(f"✓ Added '{col_name}' to income")

            # Set defaults from month field
            if 'date' in [c[0] for c in missing_columns]:
                conn.execute(sa.text("UPDATE income SET date = month || '-01' WHERE date IS NULL"))

    # ========== INCOME_SOURCES TABLE ==========
    print("\n=== Syncing income_sources table ===")
    if 'income_sources' in inspector.get_table_names():
        columns = {col['name']: col for col in inspector.get_columns('income_sources')}
        print(f"Current columns: {list(columns.keys())}")

        missing_columns = []

        if 'created_at' not in columns:
            missing_columns.append(('created_at', sa.DateTime, True))

        if missing_columns:
            with op.batch_alter_table('income_sources', schema=None) as batch_op:
                for col_name, col_type, nullable in missing_columns:
                    batch_op.add_column(sa.Column(col_name, col_type, nullable=nullable))
                    print(f"✓ Added '{col_name}' to income_sources")

    print("\n✅ All tables synced successfully!")


def downgrade():
    """This migration is one-way only."""
    pass
