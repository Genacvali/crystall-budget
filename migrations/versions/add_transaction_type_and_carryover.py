"""Add transaction_type and carryover_from_month to expenses

Revision ID: add_transaction_type_carryover
Revises: ensure_expenses_description
Create Date: 2025-10-04 00:20:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

# revision identifiers, used by Alembic.
revision = 'add_transaction_type_carryover'
down_revision = 'ensure_expenses_description'
branch_labels = None
depends_on = None


def upgrade():
    """Add transaction_type and carryover_from_month columns."""
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    columns = [col['name'] for col in inspector.get_columns('expenses')]

    # Add transaction_type column if missing
    if 'transaction_type' not in columns:
        with op.batch_alter_table('expenses', schema=None) as batch_op:
            batch_op.add_column(sa.Column('transaction_type', sa.String(20), nullable=True, server_default='expense'))

        # Set default value for existing rows
        conn.execute(sa.text("UPDATE expenses SET transaction_type = 'expense' WHERE transaction_type IS NULL"))
        print("✓ Added 'transaction_type' column to expenses table")
    else:
        print("✓ Column 'transaction_type' already exists in expenses table")

    # Add carryover_from_month column if missing
    if 'carryover_from_month' not in columns:
        with op.batch_alter_table('expenses', schema=None) as batch_op:
            batch_op.add_column(sa.Column('carryover_from_month', sa.String(7), nullable=True))
        print("✓ Added 'carryover_from_month' column to expenses table")
    else:
        print("✓ Column 'carryover_from_month' already exists in expenses table")


def downgrade():
    """Remove transaction_type and carryover_from_month columns."""
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    columns = [col['name'] for col in inspector.get_columns('expenses')]

    if 'carryover_from_month' in columns:
        with op.batch_alter_table('expenses', schema=None) as batch_op:
            batch_op.drop_column('carryover_from_month')

    if 'transaction_type' in columns:
        with op.batch_alter_table('expenses', schema=None) as batch_op:
            batch_op.drop_column('transaction_type')
