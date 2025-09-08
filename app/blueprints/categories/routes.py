"""Categories routes."""

import sqlite3
from flask import Blueprint, render_template, request, flash, redirect, url_for, session

from app.db import get_db
from app.services.validation import validate_amount, sanitize_string
from app.blueprints.auth.decorators import login_required

bp = Blueprint('categories', __name__)


@bp.route('/')
@login_required
def list():
    """Display categories page with all user categories."""
    uid = session["user_id"]
    conn = get_db()
    
    # Получаем все категории с типами
    rows = conn.execute(
        "SELECT *, COALESCE(category_type, 'expense') as category_type FROM categories WHERE user_id=? ORDER BY category_type, name", (uid,)
    ).fetchall()
    
    sources = conn.execute(
        "SELECT id, name FROM income_sources WHERE user_id=? ORDER BY name", (uid,)
    ).fetchall()
    rules = conn.execute(
        "SELECT category_id, source_id FROM source_category_rules WHERE user_id=?", (uid,)
    ).fetchall()
    rules_map = {r["category_id"]: r["source_id"] for r in rules}
    
    # Разделяем категории по типам
    expense_categories = [cat for cat in rows if cat["category_type"] == "expense"]
    income_categories = [cat for cat in rows if cat["category_type"] == "income"]
    
    conn.close()
    return render_template("categories/categories.html", 
                         categories=rows, 
                         expense_categories=expense_categories,
                         income_categories=income_categories,
                         income_sources=sources, 
                         rules_map=rules_map)


@bp.route('/add', methods=["POST"])
@login_required
def add():
    """Add new category."""
    uid = session["user_id"]
    name = sanitize_string(request.form.get("name"))
    limit_type = request.form.get("limit_type")
    value = request.form.get("value")
    source_id = request.form.get("source_id")
    category_type = request.form.get("category_type", "expense")  # по умолчанию тратная категория

    if not name or not limit_type or not value:
        flash("Пожалуйста, заполните все поля", "error")
        return redirect(url_for("categories.list"))
        
    if category_type not in ["expense", "income"]:
        category_type = "expense"

    amount = validate_amount(value)
    if amount is None:
        flash("Введите корректное значение лимита", "error")
        return redirect(url_for("categories.list"))

    conn = get_db()
    try:
        # Создаем категорию
        cursor = conn.execute(
            "INSERT INTO categories (user_id, name, limit_type, value, category_type) VALUES (?,?,?,?,?)",
            (uid, name, limit_type, amount, category_type),
        )
        category_id = cursor.lastrowid
        
        # Если выбран источник, создаем привязку
        if source_id:
            # Проверяем, что источник принадлежит пользователю
            valid_source = conn.execute(
                "SELECT 1 FROM income_sources WHERE id=? AND user_id=?",
                (source_id, uid)
            ).fetchone()
            
            if valid_source:
                conn.execute(
                    "INSERT INTO source_category_rules(user_id, source_id, category_id) VALUES (?,?,?)",
                    (uid, source_id, category_id)
                )
        
        conn.commit()
        flash("Категория добавлена", "success")
    except sqlite3.IntegrityError:
        flash("Категория с таким названием уже существует", "error")
    finally:
        conn.close()

    return redirect(url_for("categories.list"))


@bp.route('/update/<int:cat_id>', methods=["POST"])
@login_required
def update(cat_id):
    """Update existing category."""
    uid = session["user_id"]
    name = (request.form.get("name") or "").strip()
    limit_type = request.form.get("limit_type")
    value = request.form.get("value")
    source_id = request.form.get("source_id")

    if not name or not limit_type or not value:
        flash("Пожалуйста, заполните все поля", "error")
        return redirect(url_for("categories.list"))

    try:
        val = float(value)
        if val <= 0:
            raise ValueError
    except Exception:
        flash("Введите корректное значение лимита", "error")
        return redirect(url_for("categories.list"))

    conn = get_db()
    
    # Обновляем категорию
    conn.execute(
        """
        UPDATE categories
           SET name=?, limit_type=?, value=?
         WHERE id=? AND user_id=?
        """,
        (name, limit_type, val, cat_id, uid),
    )
    
    # Обновляем привязку к источнику
    existing_rule = conn.execute(
        "SELECT id FROM source_category_rules WHERE user_id=? AND category_id=?",
        (uid, cat_id)
    ).fetchone()
    
    if source_id:
        # Проверяем, что источник принадлежит пользователю
        valid_source = conn.execute(
            "SELECT 1 FROM income_sources WHERE id=? AND user_id=?",
            (source_id, uid)
        ).fetchone()
        
        if valid_source:
            if existing_rule:
                conn.execute(
                    "UPDATE source_category_rules SET source_id=? WHERE id=?",
                    (source_id, existing_rule["id"])
                )
            else:
                conn.execute(
                    "INSERT INTO source_category_rules(user_id, source_id, category_id) VALUES (?,?,?)",
                    (uid, source_id, cat_id)
                )
    else:
        # Удаляем привязку, если источник не выбран
        if existing_rule:
            conn.execute(
                "DELETE FROM source_category_rules WHERE id=?",
                (existing_rule["id"],)
            )
    
    conn.commit()
    conn.close()
    flash("Категория обновлена", "success")
    return redirect(url_for("categories.list"))


@bp.route('/delete/<int:cat_id>', methods=["POST"])
@login_required
def delete(cat_id):
    """Delete category."""
    uid = session["user_id"]
    conn = get_db()
    conn.execute("DELETE FROM categories WHERE id=? AND user_id=?", (cat_id, uid))
    conn.commit()
    conn.close()
    flash("Категория удалена", "success")
    return redirect(url_for("categories.list"))