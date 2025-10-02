#!/usr/bin/env python3
"""Compare database schemas between old and new databases."""
import sqlite3
import sys
from collections import defaultdict

def get_schema_info(db_path):
    """Get complete schema information from database."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    schema = {
        'tables': {},
        'indexes': defaultdict(list),
        'foreign_keys': defaultdict(list)
    }

    # Get all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    tables = [row[0] for row in cursor.fetchall()]

    for table in tables:
        # Get columns
        cursor.execute(f"PRAGMA table_info({table})")
        columns = {}
        for row in cursor.fetchall():
            col_id, name, type_, notnull, default, pk = row
            columns[name] = {
                'type': type_,
                'notnull': notnull,
                'default': default,
                'pk': pk
            }
        schema['tables'][table] = columns

        # Get indexes
        cursor.execute(f"PRAGMA index_list({table})")
        for row in cursor.fetchall():
            seq, name, unique, origin, partial = row
            schema['indexes'][table].append({
                'name': name,
                'unique': unique,
                'origin': origin
            })

        # Get foreign keys
        cursor.execute(f"PRAGMA foreign_key_list({table})")
        for row in cursor.fetchall():
            id_, seq, table_ref, from_col, to_col, on_update, on_delete, match = row
            schema['foreign_keys'][table].append({
                'from': from_col,
                'to_table': table_ref,
                'to_col': to_col,
                'on_delete': on_delete
            })

    conn.close()
    return schema

def compare_schemas(old_db, new_db):
    """Compare two database schemas and report differences."""
    print("="*80)
    print("DATABASE SCHEMA COMPARISON")
    print("="*80)
    print(f"\nOLD DB: {old_db}")
    print(f"NEW DB: {new_db}\n")

    old_schema = get_schema_info(old_db)
    new_schema = get_schema_info(new_db)

    differences = []

    # Compare tables
    print("\n" + "="*80)
    print("TABLES COMPARISON")
    print("="*80)

    old_tables = set(old_schema['tables'].keys())
    new_tables = set(new_schema['tables'].keys())

    # Tables only in old DB
    only_old = old_tables - new_tables
    if only_old:
        print(f"\n❌ Tables ONLY in OLD DB ({len(only_old)}):")
        for table in sorted(only_old):
            print(f"   - {table}")
            differences.append(f"Table missing in new DB: {table}")

    # Tables only in new DB
    only_new = new_tables - old_tables
    if only_new:
        print(f"\n✅ Tables ONLY in NEW DB ({len(only_new)}):")
        for table in sorted(only_new):
            print(f"   + {table}")

    # Tables in both - compare columns
    common_tables = old_tables & new_tables
    print(f"\n📋 Common tables ({len(common_tables)}): {', '.join(sorted(common_tables))}")

    # Compare columns for each common table
    print("\n" + "="*80)
    print("COLUMNS COMPARISON")
    print("="*80)

    for table in sorted(common_tables):
        old_cols = set(old_schema['tables'][table].keys())
        new_cols = set(new_schema['tables'][table].keys())

        # Columns only in old
        only_old_cols = old_cols - new_cols
        if only_old_cols:
            print(f"\n❌ Table '{table}' - columns MISSING in NEW DB:")
            for col in sorted(only_old_cols):
                col_info = old_schema['tables'][table][col]
                print(f"   - {col} {col_info['type']}")
                differences.append(f"{table}.{col} missing in new DB")

        # Columns only in new
        only_new_cols = new_cols - old_cols
        if only_new_cols:
            print(f"\n✅ Table '{table}' - NEW columns in NEW DB:")
            for col in sorted(only_new_cols):
                col_info = new_schema['tables'][table][col]
                print(f"   + {col} {col_info['type']}")

    # Compare indexes
    print("\n" + "="*80)
    print("INDEXES COMPARISON")
    print("="*80)

    for table in sorted(common_tables):
        old_idx = {idx['name'] for idx in old_schema['indexes'].get(table, [])}
        new_idx = {idx['name'] for idx in new_schema['indexes'].get(table, [])}

        only_old_idx = old_idx - new_idx
        if only_old_idx:
            print(f"\n❌ Table '{table}' - indexes MISSING in NEW DB:")
            for idx_name in sorted(only_old_idx):
                print(f"   - {idx_name}")
                differences.append(f"Index {idx_name} on {table} missing in new DB")

        only_new_idx = new_idx - old_idx
        if only_new_idx:
            print(f"\n✅ Table '{table}' - NEW indexes in NEW DB:")
            for idx_name in sorted(only_new_idx):
                print(f"   + {idx_name}")

    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)

    if differences:
        print(f"\n⚠️  Found {len(differences)} differences that need migration:")
        for i, diff in enumerate(differences, 1):
            print(f"   {i}. {diff}")
    else:
        print("\n✅ No differences found - schemas are compatible!")

    return differences

if __name__ == '__main__':
    old_db = 'instance/budget.db_01_10'
    new_db = 'instance/budget.db'

    if len(sys.argv) > 1:
        old_db = sys.argv[1]
    if len(sys.argv) > 2:
        new_db = sys.argv[2]

    differences = compare_schemas(old_db, new_db)

    if differences:
        sys.exit(1)
    else:
        sys.exit(0)
