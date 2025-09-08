"""Goals routes."""

from datetime import datetime
from flask import Blueprint, request, session, redirect, url_for, flash, render_template, current_app

from ...db import get_db
from ..auth.decorators import login_required

bp = Blueprint('goals', __name__)


@bp.route('/')
@login_required
def list():
    """Страница целей накоплений."""
    conn = get_db()
    user_id = session['user_id']
    
    # Получаем все цели пользователя
    cursor = conn.execute("""
    SELECT * FROM savings_goals 
    WHERE user_id = ? 
    ORDER BY created_at DESC
    """, (user_id,))
    
    goals = cursor.fetchall()
    conn.close()
    
    return render_template('goals/goals.html', goals=goals)


@bp.route('/add', methods=['POST'])
@login_required
def add():
    """Добавление новой цели накопления."""
    try:
        name = request.form.get('name', '').strip()
        target_amount = float(request.form.get('target_amount', 0))
        target_date = request.form.get('target_date', '')
        description = request.form.get('description', '').strip()
        
        if not name or target_amount <= 0:
            flash('Название и сумма цели обязательны', 'error')
            return redirect(url_for('goals.list'))
            
        conn = get_db()
        user_id = session['user_id']
        
        conn.execute("""
        INSERT INTO savings_goals (user_id, name, target_amount, target_date, description)
        VALUES (?, ?, ?, ?, ?)
        """, (user_id, name, target_amount, target_date if target_date else None, description))
        
        conn.commit()
        conn.close()
        
        flash(f'Цель "{name}" добавлена', 'success')
        
    except Exception as e:
        current_app.logger.error(f"Error adding goal: {e}")
        flash('Ошибка при добавлении цели', 'error')
        
    return redirect(url_for('goals.list'))


@bp.route('/update/<int:goal_id>', methods=['POST'])
@login_required
def update_progress(goal_id):
    """Обновление прогресса цели."""
    try:
        amount_to_add = float(request.form.get('amount', 0))
        
        if amount_to_add <= 0:
            flash('Сумма должна быть положительной', 'error')
            return redirect(url_for('goals.list'))
            
        conn = get_db()
        user_id = session['user_id']
        
        # Проверяем, что цель принадлежит пользователю
        cursor = conn.execute("""
        SELECT current_amount, target_amount FROM savings_goals 
        WHERE id = ? AND user_id = ?
        """, (goal_id, user_id))
        
        goal = cursor.fetchone()
        if not goal:
            flash('Цель не найдена', 'error')
            return redirect(url_for('goals.list'))
            
        new_amount = float(goal['current_amount']) + amount_to_add
        
        # Проверяем, достигнута ли цель
        completed_at = None
        if new_amount >= float(goal['target_amount']):
            completed_at = datetime.now().isoformat()
            
        conn.execute("""
        UPDATE savings_goals 
        SET current_amount = ?, completed_at = ?
        WHERE id = ? AND user_id = ?
        """, (new_amount, completed_at, goal_id, user_id))
        
        conn.commit()
        conn.close()
        
        if completed_at:
            flash('🎉 Поздравляем! Цель достигнута!', 'success')
        else:
            flash(f'Добавлено {amount_to_add} к цели', 'success')
            
    except Exception as e:
        current_app.logger.error(f"Error updating goal progress: {e}")
        flash('Ошибка при обновлении прогресса', 'error')
        
    return redirect(url_for('goals.list'))


@bp.route('/delete/<int:goal_id>', methods=['POST'])
@login_required
def delete(goal_id):
    """Удаление цели накопления."""
    try:
        conn = get_db()
        user_id = session['user_id']
        
        # Проверяем, что цель принадлежит пользователю
        cursor = conn.execute("""
        SELECT name FROM savings_goals 
        WHERE id = ? AND user_id = ?
        """, (goal_id, user_id))
        
        goal = cursor.fetchone()
        if not goal:
            flash('Цель не найдена', 'error')
            return redirect(url_for('goals.list'))
            
        goal_name = goal['name']
        
        # Удаляем цель
        conn.execute("DELETE FROM savings_goals WHERE id = ? AND user_id = ?", (goal_id, user_id))
        conn.commit()
        conn.close()
        
        flash(f'Цель "{goal_name}" удалена', 'success')
        
    except Exception as e:
        current_app.logger.error(f"Error deleting goal: {e}")
        flash('Ошибка при удалении цели', 'error')
        
    return redirect(url_for('goals.list'))


@bp.route('/edit/<int:goal_id>', methods=['GET', 'POST'])
@login_required
def edit(goal_id):
    """Редактирование цели накопления."""
    conn = get_db()
    user_id = session['user_id']
    
    # Получаем цель
    cursor = conn.execute("""
    SELECT * FROM savings_goals 
    WHERE id = ? AND user_id = ?
    """, (goal_id, user_id))
    
    goal = cursor.fetchone()
    if not goal:
        conn.close()
        flash('Цель не найдена', 'error')
        return redirect(url_for('goals.list'))
    
    if request.method == 'POST':
        try:
            name = request.form.get('name', '').strip()
            target_amount = float(request.form.get('target_amount', 0))
            target_date = request.form.get('target_date', '')
            description = request.form.get('description', '').strip()
            
            if not name or target_amount <= 0:
                flash('Название и сумма цели обязательны', 'error')
                return redirect(url_for('goals.edit', goal_id=goal_id))
            
            # Обновляем цель
            conn.execute("""
            UPDATE savings_goals 
            SET name = ?, target_amount = ?, target_date = ?, description = ?
            WHERE id = ? AND user_id = ?
            """, (name, target_amount, target_date if target_date else None, description, goal_id, user_id))
            
            conn.commit()
            conn.close()
            
            flash(f'Цель "{name}" обновлена', 'success')
            return redirect(url_for('goals.list'))
            
        except Exception as e:
            current_app.logger.error(f"Error updating goal: {e}")
            flash('Ошибка при обновлении цели', 'error')
    
    conn.close()
    return render_template('goals/edit_goal.html', goal=goal)