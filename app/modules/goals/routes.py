"""Goals module routes."""
from flask import render_template, request, redirect, url_for, flash, session, jsonify
from flask_login import login_required, current_user
from .service import GoalsService, SharedBudgetService
from .schemas import SavingsGoalForm, GoalProgressForm, SharedBudgetForm, JoinBudgetForm, MemberRoleForm
from .models import SavingsGoal, SharedBudget, SharedBudgetMember
from . import goals_bp


@goals_bp.route('/')
@login_required
def list_goals():
    """Goals list page."""
    user_id = current_user.id
    
    goals = GoalsService.get_user_goals(user_id)
    statistics = GoalsService.get_goal_statistics(user_id)
    
    return render_template('goals/list.html', 
                         goals=goals, 
                         statistics=statistics)


@goals_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create_goal():
    """Create new savings goal."""
    user_id = current_user.id
    form = SavingsGoalForm()
    
    if form.validate_on_submit():
        try:
            goal = GoalsService.create_goal(
                user_id=user_id,
                title=form.title.data,
                target_amount=form.target_amount.data,
                description=form.description.data,
                target_date=form.target_date.data,
                currency=form.currency.data
            )
            flash('Цель создана', 'success')
            return redirect(url_for('goals.list_goals'))
        except Exception as e:
            flash(f'Ошибка при создании цели: {str(e)}', 'error')
    
    return render_template('goals/goal_form.html', form=form, title='Создать цель')


@goals_bp.route('/edit/<int:goal_id>', methods=['GET', 'POST'])
@login_required
def edit_goal(goal_id):
    """Edit savings goal."""
    user_id = current_user.id
    goal = SavingsGoal.query.filter_by(id=goal_id, user_id=user_id).first_or_404()
    
    form = SavingsGoalForm(obj=goal)
    
    if form.validate_on_submit():
        try:
            GoalsService.update_goal(
                goal_id=goal_id,
                user_id=user_id,
                title=form.title.data,
                target_amount=form.target_amount.data,
                description=form.description.data,
                target_date=form.target_date.data,
                currency=form.currency.data
            )
            flash('Цель обновлена', 'success')
            return redirect(url_for('goals.list_goals'))
        except Exception as e:
            flash(f'Ошибка при обновлении цели: {str(e)}', 'error')
    
    return render_template('goals/goal_form.html', form=form, title='Редактировать цель')


@goals_bp.route('/delete/<int:goal_id>', methods=['POST'])
@login_required
def delete_goal(goal_id):
    """Delete savings goal."""
    user_id = current_user.id
    
    if GoalsService.delete_goal(goal_id, user_id):
        flash('Цель удалена', 'success')
    else:
        flash('Цель не найдена', 'error')
    
    return redirect(url_for('goals.list_goals'))


@goals_bp.route('/progress', methods=['POST'])
@login_required
def add_progress():
    """Add progress to savings goal."""
    user_id = current_user.id
    form = GoalProgressForm()
    
    if form.validate_on_submit():
        try:
            goal = GoalsService.add_progress(
                goal_id=form.goal_id.data,
                user_id=user_id,
                amount=form.amount.data
            )
            if goal:
                flash('Прогресс добавлен', 'success')
                if goal.completed:
                    flash('🎉 Поздравляем! Цель достигнута!', 'success')
            else:
                flash('Цель не найдена', 'error')
        except Exception as e:
            flash(f'Ошибка при добавлении прогресса: {str(e)}', 'error')
    else:
        flash('Ошибка в данных формы', 'error')
    
    return redirect(url_for('goals.list_goals'))


@goals_bp.route('/shared-budgets')
@login_required
def shared_budgets():
    """Shared budgets page."""
    user_id = current_user.id
    
    budgets = SharedBudgetService.get_user_shared_budgets(user_id)
    
    return render_template('goals/shared_budgets.html', budgets=budgets)


@goals_bp.route('/shared-budgets/create', methods=['GET', 'POST'])
@login_required
def create_shared_budget():
    """Create new shared budget."""
    user_id = current_user.id
    form = SharedBudgetForm()
    
    if form.validate_on_submit():
        try:
            budget = SharedBudgetService.create_shared_budget(
                user_id=user_id,
                name=form.name.data,
                description=form.description.data
            )
            flash(f'Семейный бюджет создан. Код приглашения: {budget.invitation_code}', 'success')
            return redirect(url_for('goals.shared_budgets'))
        except Exception as e:
            flash(f'Ошибка при создании бюджета: {str(e)}', 'error')
    
    return render_template('goals/shared_budget_form.html', form=form, title='Создать семейный бюджет')


@goals_bp.route('/shared-budgets/join', methods=['GET', 'POST'])
@login_required
def join_shared_budget():
    """Join shared budget by invitation code."""
    user_id = current_user.id
    form = JoinBudgetForm()
    
    if form.validate_on_submit():
        try:
            budget = SharedBudgetService.join_shared_budget(
                user_id=user_id,
                invitation_code=form.invitation_code.data
            )
            if budget:
                flash(f'Вы присоединились к бюджету "{budget.name}"', 'success')
                return redirect(url_for('goals.shared_budgets'))
            else:
                flash('Неверный код приглашения', 'error')
        except Exception as e:
            flash(f'Ошибка при присоединении: {str(e)}', 'error')
    
    return render_template('goals/join_budget_form.html', form=form)


@goals_bp.route('/shared-budgets/<int:budget_id>')
@login_required
def shared_budget_detail(budget_id):
    """Shared budget detail page."""
    user_id = current_user.id
    
    summary = SharedBudgetService.get_budget_summary(budget_id, user_id)
    if not summary:
        flash('Бюджет не найден или у вас нет доступа', 'error')
        return redirect(url_for('goals.shared_budgets'))
    
    return render_template('goals/shared_budget_detail.html', **summary)


@goals_bp.route('/shared-budgets/<int:budget_id>/members/<int:member_user_id>/remove', methods=['POST'])
@login_required
def remove_budget_member(budget_id, member_user_id):
    """Remove member from shared budget."""
    user_id = current_user.id
    
    if SharedBudgetService.remove_member(budget_id, member_user_id, user_id):
        flash('Участник удален', 'success')
    else:
        flash('Ошибка при удалении участника', 'error')
    
    return redirect(url_for('goals.shared_budget_detail', budget_id=budget_id))


@goals_bp.route('/shared-budgets/<int:budget_id>/members/<int:member_user_id>/role', methods=['POST'])
@login_required
def update_member_role(budget_id, member_user_id):
    """Update member role in shared budget."""
    user_id = current_user.id
    form = MemberRoleForm()
    
    if form.validate_on_submit():
        if SharedBudgetService.update_member_role(budget_id, member_user_id, form.role.data, user_id):
            flash('Роль участника обновлена', 'success')
        else:
            flash('Ошибка при обновлении роли', 'error')
    else:
        flash('Неверные данные', 'error')
    
    return redirect(url_for('goals.shared_budget_detail', budget_id=budget_id))


@goals_bp.route('/shared-budgets/<int:budget_id>/delete', methods=['POST'])
@login_required
def delete_shared_budget(budget_id):
    """Delete shared budget."""
    user_id = current_user.id
    
    if SharedBudgetService.delete_shared_budget(budget_id, user_id):
        flash('Семейный бюджет удален', 'success')
    else:
        flash('Ошибка при удалении бюджета', 'error')
    
    return redirect(url_for('goals.shared_budgets'))