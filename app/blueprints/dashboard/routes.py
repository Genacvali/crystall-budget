"""Dashboard routes."""

from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, session, redirect, url_for, flash

from ...db import get_db
from ..auth.decorators import login_required

bp = Blueprint('dashboard', __name__)


@bp.route('/')
@login_required
def index():
    """Main dashboard page."""
    month = request.args.get("month") or datetime.now().strftime("%Y-%m")
    conn = get_db()
    uid = session["user_id"]
    
    # Подготовка данных для навигации по месяцам
    try:
        current_date = datetime.strptime(month, "%Y-%m")
        prev_month = (current_date.replace(day=1) - timedelta(days=1)).strftime("%Y-%m")
        next_month = (current_date.replace(day=28) + timedelta(days=4)).replace(day=1).strftime("%Y-%m")
        current_month_name = current_date.strftime("%B %Y")
        
        # Переводим название месяца на русский
        month_names_ru = {
            "January": "Январь", "February": "Февраль", "March": "Март", "April": "Апрель",
            "May": "Май", "June": "Июнь", "July": "Июль", "August": "Август",
            "September": "Сентябрь", "October": "Октябрь", "November": "Ноябрь", "December": "Декабрь"
        }
        
        eng_month_name = current_date.strftime("%B")
        current_month_name = f"{month_names_ru.get(eng_month_name, eng_month_name)} {current_date.year}"
        
        month_names = ["Январь", "Февраль", "Март", "Апрель", "Май", "Июнь", 
                       "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"]
    except ValueError:
        # Если формат месяца некорректный, используем текущий
        month = datetime.now().strftime("%Y-%m")
        current_date = datetime.now()
        prev_month = (current_date.replace(day=1) - timedelta(days=1)).strftime("%Y-%m")
        next_month = (current_date.replace(day=28) + timedelta(days=4)).replace(day=1).strftime("%Y-%m")
        current_month_name = "Текущий месяц"
        month_names = ["Январь", "Февраль", "Март", "Апрель", "Май", "Июнь", 
                       "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"]

    # категории пользователя
    categories = conn.execute(
        "SELECT * FROM categories WHERE user_id=? ORDER BY name", (uid,)
    ).fetchall()

    # доход месяца из income_daily
    income_sum = conn.execute(
        """
        SELECT COALESCE(SUM(amount), 0)
        FROM income_daily
        WHERE user_id = ? AND strftime('%Y-%m', date) = ?
        """,
        (uid, month),
    ).fetchone()[0]

    # траты месяца (для списка)
    expenses_rows = conn.execute(
        """
        SELECT e.id, e.date, e.amount, e.note, c.name as category_name
        FROM expenses e
        JOIN categories c ON c.id = e.category_id
        WHERE e.user_id = ? AND e.month = ?
        ORDER BY e.date DESC, e.id DESC
        """,
        (uid, month),
    ).fetchall()

    # сумма трат по категориям
    spent_by_cat = conn.execute(
        """
        SELECT c.id, c.name, COALESCE(SUM(e.amount), 0) as spent
        FROM categories c
        LEFT JOIN expenses e ON e.category_id = c.id AND e.user_id = c.user_id AND e.month = ?
        WHERE c.user_id = ?
        GROUP BY c.id, c.name
        """,
        (month, uid),
    ).fetchall()

    # правило категория->источник (нужно раньше для расчета лимитов)
    rule_rows = conn.execute(
        "SELECT category_id, source_id FROM source_category_rules WHERE user_id=?",
        (uid,),
    ).fetchall()
    rule_map = {r["category_id"]: r["source_id"] for r in rule_rows}
    
    # приход по источникам (нужно раньше для расчета процентных лимитов)
    sources = conn.execute(
        "SELECT id, name FROM income_sources WHERE user_id=? ORDER BY name", (uid,)
    ).fetchall()
    
    income_by_source = {
        s["id"]: conn.execute(
            """
            SELECT COALESCE(SUM(amount),0) FROM income_daily
            WHERE user_id=? AND source_id=? AND strftime('%Y-%m', date)=?
            """,
            (uid, s["id"], month),
        ).fetchone()[0]
        for s in sources
    }

    # расчёт лимитов категорий с учётом процента от дохода
    limits = conn.execute(
        "SELECT id, name, limit_type, value FROM categories WHERE user_id=?",
        (uid,),
    ).fetchall()

    data = []
    for row in limits:
        cat_id = row["id"]
        limit_val = 0.0
        if row["limit_type"] == "fixed":
            limit_val = float(row["value"])
        else:  # percent
            # Если категория привязана к источнику - используем доход этого источника
            source_id = rule_map.get(cat_id)
            if source_id and source_id in income_by_source:
                source_income = float(income_by_source[source_id])
                limit_val = source_income * float(row["value"]) / 100.0
            else:
                # Если не привязана - используем общий доход
                limit_val = float(income_sum) * float(row["value"]) / 100.0

        spent = 0.0
        for s in spent_by_cat:
            if s["id"] == cat_id:
                spent = float(s["spent"])
                break

        # Получаем информацию об источнике дохода для категории
        source_id = rule_map.get(cat_id)
        source_name = None
        if source_id:
            for s in sources:
                if s["id"] == source_id:
                    source_name = s["name"]
                    break
        
        data.append(
            dict(category_name=row["name"], limit=limit_val, spent=spent, id=cat_id, source_name=source_name)
        )

    # ---- Балансы по источникам в выбранном месяце ----
    # (источники и доходы уже получены выше)

    # расход по источнику (по правилам)
    expense_by_source = {s["id"]: 0.0 for s in sources}
    # лимиты по источнику (сумма всех лимитов категорий, привязанных к источнику)
    limits_by_source = {s["id"]: 0.0 for s in sources}
    
    for cat in limits:
        cat_id = cat["id"]
        src_id = rule_map.get(cat_id)
        if not src_id:
            continue
            
        # Считаем потраченное
        spent_val = conn.execute(
            """
            SELECT COALESCE(SUM(amount),0) FROM expenses
            WHERE user_id=? AND month=? AND category_id=?
            """,
            (uid, month, cat_id),
        ).fetchone()[0]
        expense_by_source[src_id] += float(spent_val)
        
        # Считаем лимит этой категории
        if cat["limit_type"] == "fixed":
            limit_val = float(cat["value"])
        else:  # percent
            source_income = float(income_by_source.get(src_id, 0))
            limit_val = source_income * float(cat["value"]) / 100.0
        limits_by_source[src_id] += limit_val

    source_balances = []
    for s in sources:
        sid = s["id"]
        inc = float(income_by_source.get(sid, 0.0))
        sp = float(expense_by_source.get(sid, 0.0))
        limits_total = float(limits_by_source.get(sid, 0.0))
        remaining_after_limits = inc - limits_total  # остается после всех запланированных лимитов
        source_balances.append(
            dict(source_id=sid, source_name=s["name"], income=inc, spent=sp, 
                 rest=inc - sp, limits_total=limits_total, remaining_after_limits=remaining_after_limits)
        )

    conn.close()

    today = datetime.now().strftime("%Y-%m-%d")
    return render_template(
        "dashboard/dashboard.html",
        categories=categories,
        expenses=expenses_rows,
        budget_data=data,
        income=income_sum,
        current_month=month,
        current_month_name=current_month_name,
        prev_month=prev_month,
        next_month=next_month,
        month_names=month_names,
        today=today,
        source_balances=source_balances,
        sources=sources,
    )


@bp.route("/quick-expense", methods=["POST"])
@login_required
def quick_expense():
    """Quick expense entry from dashboard."""
    uid = session["user_id"]
    date_str = request.form.get("date", "").strip()
    category_id = request.form.get("category_id", "").strip()
    amount_str = request.form.get("amount", "").strip()
    note = (request.form.get("note") or "").strip()
    return_month = request.form.get("return_month") or datetime.now().strftime("%Y-%m")

    if not date_str or not category_id or not amount_str:
        flash("Пожалуйста, заполните все поля", "error")
        return redirect(url_for("dashboard.index", month=return_month))

    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        amount = float(amount_str)
        if amount <= 0:
            raise ValueError
    except Exception:
        flash("Неверные значения даты или суммы", "error")
        return redirect(url_for("dashboard.index", month=return_month))

    conn = get_db()
    conn.execute(
        """
        INSERT INTO expenses (user_id, date, month, category_id, amount, note)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (uid, date_str, date_str[:7], int(category_id), amount, note),
    )
    conn.commit()
    conn.close()
    flash("Расход добавлен", "success")
    return redirect(url_for("dashboard.index", month=return_month))