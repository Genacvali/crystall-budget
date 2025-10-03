"""Ensure expenses table has description column

Revision ID: ensure_expenses_description
Revises: add_shared_budget_to_users
Create Date: 2025-10-04 00:15:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

# revision identifiers, used by Alembic.
revision = 'ensure_expenses_description'
down_revision = 'add_shared_budget_to_users'
branch_labels = None
depends_on = None


def upgrade():
    """Add description column to expenses if it doesn't exist."""
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    columns = [col['name'] for col in inspector.get_columns('expenses')]

    # Add description column if missing
    if 'description' not in columns:
        with op.batch_alter_table('expenses', schema=None) as batch_op:
            batch_op.add_column(sa.Column('description', sa.Text(), nullable=True))
        print("✓ Added 'description' column to expenses table")
    else:
        print("✓ Column 'description' already exists in expenses table")

    # Check if note column exists and has data
    if 'note' in columns:
        # Migrate data from note to description if description is empty
        conn.execute(sa.text("""
            UPDATE expenses
            SET description = note
            WHERE description IS NULL AND note IS NOT NULL
        """))
        print("✓ Migrated data from 'note' to 'description'")


def downgrade():
    """Remove description column."""
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    columns = [col['name'] for col in inspector.get_columns('expenses')]

    if 'description' in columns:
        with op.batch_alter_table('expenses', schema=None) as batch_op:
            batch_op.drop_column('description')
