"""Add date field to income table

Revision ID: add_date_to_income
Revises: d06c52a8b6a7
Create Date: 2025-09-25 22:10:00.000000

"""
from alembic import op
import sqlalchemy as sa
from datetime import date

# revision identifiers, used by Alembic.
revision = 'add_date_to_income'
down_revision = 'd06c52a8b6a7'
branch_labels = None
depends_on = None


def upgrade():
    # Add date column as nullable initially
    op.add_column('income', sa.Column('date', sa.Date(), nullable=True))
    
    # Populate date field from existing year/month data
    connection = op.get_bind()
    connection.execute(sa.text("""
        UPDATE income 
        SET date = date(year || '-' || printf('%02d', month) || '-01')
        WHERE year IS NOT NULL AND month IS NOT NULL
    """))


def downgrade():
    # Remove date column
    op.drop_column('income', 'date')