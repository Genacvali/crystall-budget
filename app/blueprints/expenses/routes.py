"""Expenses routes."""
import sqlite3
from datetime import datetime
from flask import Blueprint, render_template, request, flash, redirect, url_for, session
from app.blueprints.auth.decorators import login_required
from app.services.validation import validate_amount, validate_date, sanitize_string
from app.db import get_db

bp = Blueprint('expenses', __name__)

@bp.route('/', methods=["GET", "POST"])
@login_required
def list_add():
    uid = session["user_id"]

    if request.method == "POST":
        date_str = validate_date(request.form.get("date"))
        category_id = request.form.get("category_id")
        amount = validate_amount(request.form.get("amount"))
        note = sanitize_string(request.form.get("note"), 500)

        if not date_str or not category_id or amount is None:
            flash("Пожалуйста, заполните все обязательные поля корректно", "error")
            return redirect(url_for("expenses.list_add"))

        try:
            category_id = int(category_id)
        except (ValueError, TypeError):
            flash("Некорректная категория", "error")
            return redirect(url_for("expenses.list_add"))

        conn = get_db()
        try:
            # Сохраняем текущую валюту пользователя
            current_currency = session.get('currency', 'RUB')
            conn.execute(
                """
                INSERT INTO expenses (user_id, date, month, category_id, amount, note, currency)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (uid, date_str, date_str[:7], category_id, amount, note, current_currency),
            )
            conn.commit()
            flash("Расход добавлен", "success")
        except sqlite3.IntegrityError:
            flash("Ошибка: выбранная категория не существует", "error")
        except Exception as e:
            flash("Произошла ошибка при добавлении расхода", "error")
        finally:
            conn.close()
        return redirect(url_for("expenses.list_add"))

    # GET
    conn = get_db()
    cats = conn.execute(
        "SELECT id, name FROM categories WHERE user_id=? ORDER BY name", (uid,)
    ).fetchall()
    
    try:
        rows = conn.execute(
            """
            SELECT e.id, e.date, e.amount, e.note, e.currency, c.name AS category_name
            FROM expenses e
            JOIN categories c ON c.id = e.category_id
            WHERE e.user_id = ?
            ORDER BY e.date DESC, e.id DESC
            """,
            (uid,),
        ).fetchall()
    except sqlite3.OperationalError as e:
        if "no such column: e.currency" in str(e):
            # Fallback query without currency column
            rows = conn.execute(
                """
                SELECT e.id, e.date, e.amount, e.note, NULL AS currency, c.name AS category_name
                FROM expenses e
                JOIN categories c ON c.id = e.category_id
                WHERE e.user_id = ?
                ORDER BY e.date DESC, e.id DESC
                """,
                (uid,),
            ).fetchall()
        else:
            raise
    conn.close()
    today = datetime.now().strftime("%Y-%m-%d")
    return render_template("expenses/expenses.html", categories=cats, expenses=rows, today=today)


@bp.route('/edit/<int:expense_id>', methods=["GET", "POST"])
@login_required
def edit_expense(expense_id):
    uid = session["user_id"]
    conn = get_db()
    expense = conn.execute(
        "SELECT id, date, amount, note, category_id FROM expenses WHERE id=? AND user_id=?",
        (expense_id, uid),
    ).fetchone()
    if not expense:
        conn.close()
        flash("Расход не найден", "error")
        return redirect(url_for("expenses.list_add"))

    if request.method == "POST":
        date_str = validate_date(request.form.get("date"))
        category_id = request.form.get("category_id")
        amount = validate_amount(request.form.get("amount"))
        note = sanitize_string(request.form.get("note"), 500)

        if not date_str or not category_id or amount is None:
            flash("Пожалуйста, заполните все обязательные поля корректно", "error")
            return redirect(url_for("expenses.edit_expense", expense_id=expense_id))

        try:
            category_id = int(category_id)
        except (ValueError, TypeError):
            flash("Некорректная категория", "error")
            return redirect(url_for("expenses.edit_expense", expense_id=expense_id))

        try:
            current_currency = session.get('currency', 'RUB')
            conn.execute(
                """
                UPDATE expenses 
                SET date=?, month=?, category_id=?, amount=?, note=?, currency=?
                WHERE id=? AND user_id=?
                """,
                (date_str, date_str[:7], category_id, amount, note, current_currency, expense_id, uid),
            )
            conn.commit()
            conn.close()
            flash("Расход обновлён", "success")
            return redirect(url_for("expenses.list_add"))
        except sqlite3.IntegrityError:
            flash("Ошибка: выбранная категория не существует", "error")
        except Exception as e:
            flash("Произошла ошибка при обновлении расхода", "error")
        finally:
            conn.close()
        return redirect(url_for("expenses.edit_expense", expense_id=expense_id))

    categories = conn.execute(
        "SELECT id, name FROM categories WHERE user_id=? ORDER BY name", (uid,)
    ).fetchall()
    conn.close()
    return render_template("expenses/edit_expense.html", expense=expense, categories=categories)


@bp.route('/delete/<int:expense_id>', methods=["POST"])
@login_required
def delete_expense(expense_id):
    uid = session["user_id"]
    conn = get_db()
    conn.execute("DELETE FROM expenses WHERE id=? AND user_id=?", (expense_id, uid))
    conn.commit()
    conn.close()
    flash("Расход удалён", "success")
    return redirect(url_for("expenses.list_add"))