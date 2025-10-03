"""Add shared budget support

Revision ID: 515954c99c28
Revises: add_date_to_income
Create Date: 2025-10-03 19:05:28.612742

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '515954c99c28'
down_revision = 'add_date_to_income'
branch_labels = None
depends_on = None


def upgrade():
    # SQLite doesn't support ALTER TABLE with views, so we use raw SQL
    conn = op.get_bind()

    # Drop view if exists
    conn.execute(sa.text("DROP VIEW IF EXISTS category_limits_view"))

    # Add shared_budget_id to expenses table
    conn.execute(sa.text("ALTER TABLE expenses ADD COLUMN shared_budget_id INTEGER REFERENCES shared_budgets(id) ON DELETE CASCADE"))

    # Add shared_budget_id to categories table
    conn.execute(sa.text("ALTER TABLE categories ADD COLUMN shared_budget_id INTEGER REFERENCES shared_budgets(id) ON DELETE CASCADE"))


def downgrade():
    # SQLite doesn't support DROP COLUMN easily, so we would need to recreate tables
    # For now, we'll just pass since this is a one-way migration
    pass
