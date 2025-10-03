"""Fix income table structure - ensure id column exists

Revision ID: fix_income_table_structure
Revises: sync_all_tables_schema
Create Date: 2025-10-04 00:35:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

# revision identifiers, used by Alembic.
revision = 'fix_income_table_structure'
down_revision = 'sync_all_tables_schema'
branch_labels = None
depends_on = None


def upgrade():
    """Fix income table structure."""
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)

    if 'income' not in inspector.get_table_names():
        print("! Income table doesn't exist, creating...")
        op.create_table('income',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('source_name', sa.String(100), nullable=False),
            sa.Column('amount', sa.Numeric(10, 2), nullable=False),
            sa.Column('currency', sa.String(3), nullable=True, server_default='RUB'),
            sa.Column('date', sa.Date(), nullable=True),
            sa.Column('year', sa.Integer(), nullable=True),
            sa.Column('month', sa.Integer(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint('id'),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
            sa.UniqueConstraint('user_id', 'source_name', 'year', 'month')
        )
        print("✓ Created income table")
        return

    columns = {col['name']: col for col in inspector.get_columns('income')}
    print(f"Current income columns: {list(columns.keys())}")

    # Check if id column exists
    if 'id' not in columns:
        print("! Income table missing 'id' column - rebuilding table...")

        # Backup data
        backup_data = conn.execute(sa.text("SELECT * FROM income")).fetchall()
        backup_columns = list(columns.keys())
        print(f"✓ Backed up {len(backup_data)} income records")

        # Drop old table
        op.drop_table('income')
        print("✓ Dropped old income table")

        # Create new table with correct structure
        op.create_table('income',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('source_name', sa.String(100), nullable=False),
            sa.Column('amount', sa.Numeric(10, 2), nullable=False),
            sa.Column('currency', sa.String(3), nullable=True, server_default='RUB'),
            sa.Column('date', sa.Date(), nullable=True),
            sa.Column('year', sa.Integer(), nullable=True),
            sa.Column('month', sa.Integer(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint('id'),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
            sa.UniqueConstraint('user_id', 'source_name', 'year', 'month')
        )
        print("✓ Created new income table with id column")

        # Restore data
        if backup_data:
            # Map old columns to new columns
            for row in backup_data:
                row_dict = dict(zip(backup_columns, row))

                # Build insert with available columns
                insert_cols = []
                insert_vals = []

                for col in ['user_id', 'source_name', 'amount', 'currency', 'date', 'year', 'month', 'created_at']:
                    if col in row_dict:
                        insert_cols.append(col)
                        insert_vals.append(row_dict[col])

                if insert_cols:
                    placeholders = ', '.join(['?' for _ in insert_vals])
                    sql = f"INSERT INTO income ({', '.join(insert_cols)}) VALUES ({placeholders})"
                    conn.execute(sa.text(sql), insert_vals)

            print(f"✓ Restored {len(backup_data)} income records")
    else:
        print("✓ Income table has id column")

        # Ensure other columns exist
        missing = []
        expected = {
            'user_id': sa.Integer,
            'source_name': sa.String(100),
            'amount': sa.Numeric(10, 2),
            'currency': sa.String(3),
            'date': sa.Date,
            'year': sa.Integer,
            'month': sa.Integer,
            'created_at': sa.DateTime,
        }

        for col_name, col_type in expected.items():
            if col_name not in columns:
                missing.append((col_name, col_type))

        if missing:
            with op.batch_alter_table('income', schema=None) as batch_op:
                for col_name, col_type in missing:
                    batch_op.add_column(sa.Column(col_name, col_type, nullable=True))
                    print(f"✓ Added '{col_name}' to income")

            # Set defaults
            if 'currency' in [c[0] for c in missing]:
                conn.execute(sa.text("UPDATE income SET currency = 'RUB' WHERE currency IS NULL"))

    print("✅ Income table structure fixed!")


def downgrade():
    """This migration is one-way only."""
    pass
