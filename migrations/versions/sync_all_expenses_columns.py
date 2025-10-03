"""Sync all expenses columns with current schema

Revision ID: sync_all_expenses_columns
Revises: add_transaction_type_carryover
Create Date: 2025-10-04 00:25:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

# revision identifiers, used by Alembic.
revision = 'sync_all_expenses_columns'
down_revision = 'add_transaction_type_carryover'
branch_labels = None
depends_on = None


def upgrade():
    """Ensure all required columns exist in expenses table."""
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    columns = {col['name']: col for col in inspector.get_columns('expenses')}

    print(f"Current columns in expenses: {list(columns.keys())}")

    # Define expected schema
    expected_columns = {
        'id': {'type': sa.Integer, 'primary_key': True},
        'user_id': {'type': sa.Integer, 'nullable': False},
        'shared_budget_id': {'type': sa.Integer, 'nullable': True},
        'category_id': {'type': sa.Integer, 'nullable': False},
        'amount': {'type': sa.Numeric(10, 2), 'nullable': False},
        'description': {'type': sa.Text, 'nullable': True},
        'date': {'type': sa.Date, 'nullable': False},
        'currency': {'type': sa.String(3), 'nullable': True, 'default': 'RUB'},
        'month': {'type': sa.String(7), 'nullable': False},
        'transaction_type': {'type': sa.String(20), 'nullable': True, 'default': 'expense'},
        'carryover_from_month': {'type': sa.String(7), 'nullable': True},
        'created_at': {'type': sa.DateTime, 'nullable': True},
    }

    # Add missing columns
    with op.batch_alter_table('expenses', schema=None) as batch_op:
        for col_name, col_spec in expected_columns.items():
            if col_name not in columns and col_name != 'id':
                col_type = col_spec['type']
                nullable = col_spec.get('nullable', True)
                default = col_spec.get('default')

                if default:
                    batch_op.add_column(sa.Column(col_name, col_type, nullable=nullable, server_default=default))
                else:
                    batch_op.add_column(sa.Column(col_name, col_type, nullable=nullable))

                print(f"✓ Added column '{col_name}' to expenses table")

    # Set defaults for existing rows
    if 'transaction_type' not in columns:
        conn.execute(sa.text("UPDATE expenses SET transaction_type = 'expense' WHERE transaction_type IS NULL"))
        print("✓ Set default transaction_type for existing rows")

    if 'created_at' not in columns:
        conn.execute(sa.text("UPDATE expenses SET created_at = date WHERE created_at IS NULL"))
        print("✓ Set default created_at for existing rows")

    if 'currency' not in columns:
        conn.execute(sa.text("UPDATE expenses SET currency = 'RUB' WHERE currency IS NULL"))
        print("✓ Set default currency for existing rows")

    # Handle old 'note' column if it exists
    if 'note' in columns and 'description' in columns:
        conn.execute(sa.text("UPDATE expenses SET description = note WHERE description IS NULL AND note IS NOT NULL"))
        print("✓ Migrated data from 'note' to 'description'")

    print("✓ All expenses columns synced successfully")


def downgrade():
    """This migration is one-way only."""
    pass
