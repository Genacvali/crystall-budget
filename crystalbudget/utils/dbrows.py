"""Database row utilities"""

def row_get(row, key, default=None):
    """Safely get value from sqlite3.Row or dict"""
    if row is None:
        return default
    if isinstance(row, dict):
        return row.get(key, default)
    try:
        if hasattr(row, "keys") and key in row.keys():
            return row[key]
    except Exception:
        pass
    return default

def to_dict_list(rows):
    """Convert list of sqlite3.Row to list of dict"""
    try:
        return [dict(r) for r in rows]
    except Exception:
        return rows

def to_dict(row):
    """Convert sqlite3.Row to dict"""
    try:
        return dict(row) if row else None
    except Exception:
        return row