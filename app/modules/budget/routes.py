"""Budget module routes."""
from flask import render_template, request, redirect, url_for, flash, session, jsonify
from flask_login import login_required, current_user
from app.core.time import YearMonth, parse_year_month
from .service import BudgetService, CurrencyService
from .schemas import CategoryForm, ExpenseForm, IncomeForm, QuickExpenseForm, BudgetFilterForm
from .models import Category, Expense, Income
from . import budget_bp


@budget_bp.route('/')
@login_required
def dashboard():
    """Main dashboard page."""
    user_id = session['user_id']
    
    # Get current month from query param or use current
    ym_param = request.args.get('ym')
    try:
        year_month = parse_year_month(ym_param) if ym_param else YearMonth.current()
    except ValueError:
        year_month = YearMonth.current()
    
    # Get budget snapshot for the month
    snapshot = BudgetService.calculate_month_snapshot(user_id, year_month)
    
    # Quick expense form
    quick_form = QuickExpenseForm()
    categories = BudgetService.get_user_categories(user_id)
    
    return render_template('budget/dashboard.html', 
                         snapshot=snapshot, 
                         quick_form=quick_form,
                         categories=categories,
                         current_month=year_month)


@budget_bp.route('/expenses')
@login_required
def expenses():
    """Expenses list page."""
    user_id = session['user_id']
    
    # Get month filter
    ym_param = request.args.get('ym')
    try:
        year_month = parse_year_month(ym_param) if ym_param else YearMonth.current()
    except ValueError:
        year_month = YearMonth.current()
    
    # Get expenses for month
    expenses_list = BudgetService.get_expenses_for_month(user_id, year_month)
    categories = BudgetService.get_user_categories(user_id)
    
    # Filter form
    filter_form = BudgetFilterForm(categories=categories)
    filter_form.year_month.data = str(year_month)
    
    return render_template('budget/expenses.html',
                         expenses=expenses_list,
                         categories=categories,
                         filter_form=filter_form,
                         current_month=year_month)


@budget_bp.route('/expenses/add', methods=['GET', 'POST'])
@login_required
def add_expense():
    """Add new expense."""
    user_id = session['user_id']
    form = ExpenseForm()
    
    # Populate category choices
    categories = BudgetService.get_user_categories(user_id)
    form.category_id.choices = [(cat.id, cat.name) for cat in categories]
    
    if form.validate_on_submit():
        expense = BudgetService.add_expense(
            user_id=user_id,
            category_id=form.category_id.data,
            amount=form.amount.data,
            description=form.description.data,
            date_val=form.date.data,
            currency=form.currency.data
        )
        flash('Расход добавлен', 'success')
        return redirect(url_for('budget.expenses'))
    
    return render_template('budget/expense_form.html', form=form, title='Добавить расход')


@budget_bp.route('/expenses/edit/<int:expense_id>', methods=['GET', 'POST'])
@login_required
def edit_expense(expense_id):
    """Edit expense."""
    user_id = session['user_id']
    expense = Expense.query.filter_by(id=expense_id, user_id=user_id).first_or_404()
    
    form = ExpenseForm(obj=expense)
    categories = BudgetService.get_user_categories(user_id)
    form.category_id.choices = [(cat.id, cat.name) for cat in categories]
    
    if form.validate_on_submit():
        BudgetService.update_expense(
            expense_id=expense_id,
            user_id=user_id,
            category_id=form.category_id.data,
            amount=form.amount.data,
            description=form.description.data,
            date=form.date.data,
            currency=form.currency.data
        )
        flash('Расход обновлен', 'success')
        return redirect(url_for('budget.expenses'))
    
    return render_template('budget/expense_form.html', form=form, title='Редактировать расход')


@budget_bp.route('/expenses/delete/<int:expense_id>', methods=['POST'])
@login_required
def delete_expense(expense_id):
    """Delete expense."""
    user_id = session['user_id']
    
    if BudgetService.delete_expense(expense_id, user_id):
        flash('Расход удален', 'success')
    else:
        flash('Расход не найден', 'error')
    
    return redirect(url_for('budget.expenses'))


@budget_bp.route('/categories')
@login_required
def categories():
    """Categories management page."""
    user_id = session['user_id']
    categories_list = BudgetService.get_user_categories(user_id)
    
    return render_template('budget/categories.html', categories=categories_list)


@budget_bp.route('/categories/add', methods=['GET', 'POST'])
@login_required
def add_category():
    """Add new category."""
    user_id = session['user_id']
    form = CategoryForm()
    
    if form.validate_on_submit():
        try:
            category = BudgetService.create_category(
                user_id=user_id,
                name=form.name.data,
                limit_type=form.limit_type.data,
                value=form.value.data
            )
            flash('Категория создана', 'success')
            return redirect(url_for('budget.categories'))
        except Exception as e:
            flash(f'Ошибка при создании категории: {str(e)}', 'error')
    
    return render_template('budget/category_form.html', form=form, title='Добавить категорию')


@budget_bp.route('/categories/edit/<int:category_id>', methods=['GET', 'POST'])
@login_required
def edit_category(category_id):
    """Edit category."""
    user_id = session['user_id']
    category = Category.query.filter_by(id=category_id, user_id=user_id).first_or_404()
    
    form = CategoryForm(obj=category)
    
    if form.validate_on_submit():
        try:
            BudgetService.update_category(
                category_id=category_id,
                user_id=user_id,
                name=form.name.data,
                limit_type=form.limit_type.data,
                value=form.value.data
            )
            flash('Категория обновлена', 'success')
            return redirect(url_for('budget.categories'))
        except Exception as e:
            flash(f'Ошибка при обновлении категории: {str(e)}', 'error')
    
    return render_template('budget/category_form.html', form=form, title='Редактировать категорию')


@budget_bp.route('/categories/delete/<int:category_id>', methods=['POST'])
@login_required
def delete_category(category_id):
    """Delete category."""
    user_id = session['user_id']
    
    if BudgetService.delete_category(category_id, user_id):
        flash('Категория удалена', 'success')
    else:
        flash('Категория не найдена', 'error')
    
    return redirect(url_for('budget.categories'))


@budget_bp.route('/income', methods=['GET', 'POST'])
@login_required
def income():
    """Income management page."""
    user_id = session['user_id']
    
    # Handle POST request (add income)
    if request.method == 'POST':
        source_name = request.form.get('source_name')
        amount = request.form.get('amount')
        month_input = request.form.get('month')  # Format: YYYY-MM
        
        if source_name and amount and month_input:
            try:
                year, month = month_input.split('-')
                income = BudgetService.add_income(
                    user_id=user_id,
                    source_name=source_name,
                    amount=float(amount),
                    year=int(year),
                    month=int(month),
                    currency='RUB'
                )
                flash('Доход добавлен', 'success')
            except Exception as e:
                flash(f'Ошибка при добавлении дохода: {str(e)}', 'error')
        else:
            flash('Заполните все обязательные поля', 'error')
        
        return redirect(url_for('budget.income'))
    
    # Handle GET request (display page)
    # Get month filter
    ym_param = request.args.get('ym')
    try:
        year_month = parse_year_month(ym_param) if ym_param else YearMonth.current()
    except ValueError:
        year_month = YearMonth.current()
    
    income_list = BudgetService.get_income_for_month(user_id, year_month)
    total_income = BudgetService.get_total_income_for_month(user_id, year_month)
    
    return render_template('budget/income.html',
                         income_list=income_list,
                         total_income=total_income,
                         current_month=year_month)


@budget_bp.route('/income/add', methods=['GET', 'POST'])
@login_required
def add_income():
    """Add new income."""
    user_id = session['user_id']
    form = IncomeForm()
    
    if form.validate_on_submit():
        try:
            income = BudgetService.add_income(
                user_id=user_id,
                source_name=form.source_name.data,
                amount=form.amount.data,
                year=form.year.data,
                month=form.month.data,
                currency=form.currency.data
            )
            flash('Доход добавлен', 'success')
            return redirect(url_for('budget.income'))
        except Exception as e:
            flash(f'Ошибка при добавлении дохода: {str(e)}', 'error')
    
    return render_template('budget/income_form.html', form=form, title='Добавить доход')


@budget_bp.route('/quick-expense', methods=['POST'])
@login_required
def quick_expense():
    """Quick expense from dashboard."""
    user_id = session['user_id']
    form = QuickExpenseForm()
    
    if form.validate_on_submit():
        try:
            expense = BudgetService.add_expense(
                user_id=user_id,
                category_id=form.category_id.data,
                amount=form.amount.data,
                description=form.description.data
            )
            flash('Расход добавлен', 'success')
        except Exception as e:
            flash(f'Ошибка при добавлении расхода: {str(e)}', 'error')
    else:
        flash('Ошибка в данных формы', 'error')
    
    return redirect(url_for('budget.dashboard'))