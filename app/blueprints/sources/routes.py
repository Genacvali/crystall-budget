"""Sources routes."""

import sqlite3
from flask import Blueprint, request, session, redirect, url_for, flash, render_template

from ...db import get_db
from ..auth.decorators import login_required

bp = Blueprint('sources', __name__)


@bp.route('/')
@login_required
def list():
    """Страница управления источниками доходов."""
    uid = session["user_id"]
    conn = get_db()
    rows = conn.execute(
        "SELECT id, name, is_default FROM income_sources WHERE user_id=? ORDER BY is_default DESC, name",
        (uid,)
    ).fetchall()
    conn.close()
    return render_template("sources/sources.html", sources=rows)


@bp.route('/add', methods=["POST"])
@login_required
def add():
    """Добавление источника дохода."""
    uid = session["user_id"]
    name = (request.form.get("name") or "").strip()
    is_default = 1 if request.form.get("is_default") == "1" else 0
    if not name:
        flash("Введите название источника", "error")
        return redirect(url_for("sources.list"))

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
    return redirect(url_for("sources.list"))


@bp.route('/update/<int:source_id>', methods=["POST"])
@login_required
def update(source_id):
    """Обновление источника дохода."""
    uid = session["user_id"]
    name = (request.form.get("name") or "").strip()
    is_default = 1 if request.form.get("is_default") == "1" else 0
    if not name:
        flash("Введите название источника", "error")
        return redirect(url_for("sources.list"))
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
    return redirect(url_for("sources.list"))


@bp.route('/delete/<int:source_id>', methods=["POST"])
@login_required
def delete(source_id):
    """Удаление источника дохода."""
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
        return redirect(url_for("sources.list"))
    
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
    return redirect(url_for("sources.list"))