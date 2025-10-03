"""add_shared_budget_to_users

Revision ID: add_shared_budget_to_users
Revises: 515954c99c28
Create Date: 2025-10-03 19:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_shared_budget_to_users'
down_revision = '515954c99c28'
branch_labels = None
depends_on = None


def upgrade():
    # Add shared_budget_id to users table
    conn = op.get_bind()

    # Check if column already exists
    result = conn.execute(sa.text("PRAGMA table_info(users)"))
    columns = [row[1] for row in result]

    if 'shared_budget_id' not in columns:
        conn.execute(sa.text(
            "ALTER TABLE users ADD COLUMN shared_budget_id INTEGER REFERENCES shared_budgets(id) ON DELETE SET NULL"
        ))

    # Remove shared_budget_id from expenses table (data migration needed)
    # First, check if column exists
    result = conn.execute(sa.text("PRAGMA table_info(expenses)"))
    columns = [row[1] for row in result]

    if 'shared_budget_id' in columns:
        # For now, we'll keep it to avoid data loss
        # In production, you'd want to migrate the data first
        pass

    # Remove shared_budget_id from categories table
    result = conn.execute(sa.text("PRAGMA table_info(categories)"))
    columns = [row[1] for row in result]

    if 'shared_budget_id' in columns:
        # For now, we'll keep it to avoid data loss
        pass


def downgrade():
    # Remove shared_budget_id from users table
    # SQLite doesn't support DROP COLUMN easily, so we skip
    pass
