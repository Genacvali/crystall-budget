"""Income routes."""

import sqlite3
from datetime import datetime
from flask import Blueprint, request, session, redirect, url_for, flash, render_template, render_template_string

from ...db import get_db, get_default_source_id
from ..auth.decorators import login_required

DEFAULT_CURRENCY = "RUB"

bp = Blueprint('income', __name__)


@bp.route('/')
@login_required
def list():
    """Income list page."""
    uid = session["user_id"]
    conn = get_db()
    try:
        rows = conn.execute(
            """
            SELECT id, date, amount, source_id, currency
            FROM income_daily
            WHERE user_id = ?
            ORDER BY date DESC, id DESC
            """,
            (uid,),
        ).fetchall()
    except sqlite3.OperationalError as e:
        if "no such column: currency" in str(e):
            # Fallback query without currency column
            rows = conn.execute(
                """
                SELECT id, date, amount, source_id, NULL AS currency
                FROM income_daily
                WHERE user_id = ?
                ORDER BY date DESC, id DESC
                """,
                (uid,),
            ).fetchall()
        else:
            raise
    income_sources = conn.execute(
        "SELECT id, name, is_default FROM income_sources WHERE user_id=? ORDER BY is_default DESC, name",
        (uid,)
    ).fetchall()
    conn.close()
    today = datetime.now().strftime("%Y-%m-%d")
    return render_template("income/income.html", incomes=rows, income_sources=income_sources, today=today)


@bp.route("/add", methods=["POST"])
@login_required
def add():
    """Add new income entry."""
    uid = session["user_id"]
    date_str = (request.form.get("date") or "").strip()
    amount_str = (request.form.get("amount") or "").strip()
    source_id = request.form.get("source_id")

    if not date_str or not amount_str:
        flash("Пожалуйста, заполните все поля", "error")
        return redirect(url_for("income.list"))

    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        amount = float(amount_str)
        if amount <= 0:
            raise ValueError
    except Exception:
        flash("Неверные значения даты или суммы", "error")
        return redirect(url_for("income.list"))

    conn = get_db()
    if not source_id:
        source_id = get_default_source_id(conn, uid)
    
    # Сохраняем текущую валюту пользователя
    current_currency = session.get('currency', DEFAULT_CURRENCY)
    conn.execute(
        "INSERT INTO income_daily (user_id, date, amount, source_id, currency) VALUES (?,?,?,?,?)",
        (uid, date_str, amount, source_id, current_currency),
    )
    conn.commit()
    conn.close()
    flash("Доход добавлен", "success")
    return redirect(url_for("income.list"))


@bp.route("/edit/<int:income_id>", methods=["GET", "POST"])
@login_required
def edit(income_id):
    """Edit income entry."""
    uid = session["user_id"]
    conn = get_db()
    row = conn.execute(
        "SELECT id, date, amount, source_id FROM income_daily WHERE id=? AND user_id=?",
        (income_id, uid),
    ).fetchone()
    if not row:
        conn.close()
        flash("Запись не найдена", "error")
        return redirect(url_for("income.list"))

    sources = conn.execute(
        "SELECT id, name FROM income_sources WHERE user_id=? ORDER BY name", (uid,)
    ).fetchall()

    if request.method == "POST":
        date_str = (request.form.get("date") or "").strip()
        amount_str = (request.form.get("amount") or "").strip()
        source_id = request.form.get("source_id") or None
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
            amount = float(amount_str)
            if amount <= 0:
                raise ValueError
        except Exception:
            flash("Неверные значения", "error")
            return redirect(url_for("income.edit", income_id=income_id))

        conn.execute(
            "UPDATE income_daily SET date=?, amount=?, source_id=? WHERE id=? AND user_id=?",
            (date_str, amount, source_id, income_id, uid),
        )
        conn.commit()
        conn.close()
        flash("Доход обновлён", "success")
        return redirect(url_for("income.list"))

    conn.close()
    return render_template_string(
        """
        {% extends "base.html" %}
        {% block title %}Редактировать доход{% endblock %}
        {% block content %}
        <div class="container" style="max-width:560px">
          <h3 class="mb-3">Редактировать доход</h3>
          <form method="post">
            <div class="mb-3">
              <label class="form-label">Дата</label>
              <input class="form-control" type="date" name="date" value="{{ income.date }}" required>
            </div>
            <div class="mb-3">
              <label class="form-label">Сумма</label>
              <input class="form-control" type="number" name="amount" step="0.01" min="0.01" value="{{ income.amount }}" required>
            </div>
            <div class="mb-3">
              <label class="form-label">Источник</label>
              <select class="form-select" name="source_id">
                <option value="">(не указан)</option>
                {% for s in sources %}
                  <option value="{{ s.id }}" {% if income.source_id == s.id %}selected{% endif %}>{{ s.name }}</option>
                {% endfor %}
              </select>
            </div>
            <div class="d-flex gap-2">
              <button class="btn btn-primary">Сохранить</button>
              <a class="btn btn-secondary" href="{{ url_for('income.list') }}">Отмена</a>
            </div>
          </form>
        </div>
        {% endblock %}
        """,
        income=row, sources=sources,
    )


@bp.route("/delete/<int:income_id>", methods=["POST"])
@login_required
def delete(income_id):
    """Delete income entry."""
    uid = session["user_id"]
    conn = get_db()
    conn.execute("DELETE FROM income_daily WHERE id=? AND user_id=?", (income_id, uid))
    conn.commit()
    conn.close()
    flash("Доход удалён", "success")
    return redirect(url_for("income.list"))


# Income Sources management routes
@bp.route("/sources")
@login_required
def sources_list():
    """List income sources."""
    uid = session["user_id"]
    conn = get_db()
    rows = conn.execute(
        "SELECT id, name, is_default FROM income_sources WHERE user_id=? ORDER BY is_default DESC, name",
        (uid,)
    ).fetchall()
    conn.close()
    return render_template("income/sources.html", sources=rows)


@bp.route("/sources/add", methods=["POST"])
@login_required
def sources_add():
    """Add income source."""
    uid = session["user_id"]
    name = (request.form.get("name") or "").strip()
    is_default = 1 if request.form.get("is_default") == "1" else 0
    if not name:
        flash("Введите название источника", "error")
        return redirect(url_for("income.sources_list"))

    conn = get_db()
    try:
        if is_default:
            conn.execute("UPDATE income_sources SET is_default=0 WHERE user_id=?", (uid,))
        conn.execute(
            "INSERT INTO income_sources(user_id, name, is_default) VALUES (?,?,?)",
            (uid, name, is_default)
        )
        conn.commit()
        flash("Источник добавлен", "success")
    except sqlite3.IntegrityError:
        flash("Источник с таким названием уже существует", "error")
    finally:
        conn.close()
    return redirect(url_for("income.sources_list"))


@bp.route("/sources/update/<int:source_id>", methods=["POST"])
@login_required
def sources_update(source_id):
    """Update income source."""
    uid = session["user_id"]
    name = (request.form.get("name") or "").strip()
    is_default = 1 if request.form.get("is_default") == "1" else 0
    if not name:
        flash("Введите название источника", "error")
        return redirect(url_for("income.sources_list"))
    conn = get_db()
    if is_default:
        conn.execute("UPDATE income_sources SET is_default=0 WHERE user_id=?", (uid,))
    conn.execute(
        "UPDATE income_sources SET name=?, is_default=? WHERE id=? AND user_id=?",
        (name, is_default, source_id, uid)
    )
    conn.commit()
    conn.close()
    flash("Источник обновлён", "success")
    return redirect(url_for("income.sources_list"))


@bp.route("/sources/delete/<int:source_id>", methods=["POST"])
@login_required
def sources_delete(source_id):
    """Delete income source."""
    uid = session["user_id"]
    conn = get_db()
    
    # Подсчитаем связанные записи для информации
    income_count = conn.execute(
        "SELECT COUNT(*) FROM income_daily WHERE user_id=? AND source_id=?",
        (uid, source_id)
    ).fetchone()[0]
    
    rule_count = conn.execute(
        "SELECT COUNT(*) FROM source_category_rules WHERE user_id=? AND source_id=?", 
        (uid, source_id)
    ).fetchone()[0]
    
    # Получим название источника для сообщения
    source_name = conn.execute(
        "SELECT name FROM income_sources WHERE id=? AND user_id=?",
        (source_id, uid)
    ).fetchone()
    
    if not source_name:
        conn.close()
        flash("Источник не найден", "error")
        return redirect(url_for("income.sources_list"))
    
    source_name = source_name[0]
    
    # Удаляем привязки к категориям (делаем их неназначенными)
    if rule_count > 0:
        conn.execute(
            "DELETE FROM source_category_rules WHERE user_id=? AND source_id=?",
            (uid, source_id)
        )
    
    # Обнуляем source_id в доходах (делаем их неназначенными)
    if income_count > 0:
        conn.execute(
            "UPDATE income_daily SET source_id=NULL WHERE user_id=? AND source_id=?",
            (uid, source_id)
        )
    
    # Удаляем источник
    conn.execute("DELETE FROM income_sources WHERE id=? AND user_id=?", (source_id, uid))
    conn.commit()
    conn.close()
    
    # Составляем сообщение об удалении
    msg_parts = [f"Источник '{source_name}' удалён"]
    if income_count > 0:
        msg_parts.append(f"{income_count} записей дохода стали неназначенными")
    if rule_count > 0:
        msg_parts.append(f"{rule_count} правил распределения удалено")
    
    flash(". ".join(msg_parts), "success")
    return redirect(url_for("income.sources_list"))