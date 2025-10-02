"""Budget module routes."""
import datetime
from decimal import Decimal
from flask import render_template, request, redirect, url_for, flash, session, jsonify, make_response
from flask_login import login_required, current_user
from app.core.time import YearMonth, parse_year_month
from app.core.monitoring import monitor_modal_performance
from .service import BudgetService, CurrencyService, DashboardService
from .schemas import CategoryForm, ExpenseForm, IncomeForm, QuickExpenseForm, BudgetFilterForm
from .models import Category, Expense, Income, IncomeSource
from . import budget_bp


@budget_bp.route('/design-test')
def design_system_test():
    """Design system test page (temporary)."""
    return render_template('design-system-test.html')


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
    
    # Check if we need to process carryovers for month transitions
    # Create carryover for any viewed month if it doesn't exist yet
    from app.modules.budget.models import Expense

    # Check if carryovers already exist for this month
    existing_carryovers = Expense.query.filter(
        Expense.user_id == user_id,
        Expense.date >= year_month.to_date(),
        Expense.date <= year_month.last_day(),
        Expense.transaction_type == 'carryover'
    ).count()

    if existing_carryovers == 0 and year_month > YearMonth(2025, 9):
        # No carryovers exist yet, create them from previous month
        # Only create if not the first tracked month
        prev_month = year_month.prev_month()
        DashboardService.process_month_carryovers(user_id, prev_month, year_month)
    
    # Get budget snapshot for the month
    snapshot = BudgetService.calculate_month_snapshot(user_id, year_month)
    
    # Get income tiles for dashboard
    income_tiles = DashboardService.get_income_tiles(user_id, year_month)
    
    # Quick expense form
    quick_form = QuickExpenseForm()
    categories = BudgetService.get_user_categories(user_id)
    income_sources = BudgetService.get_user_income_sources(user_id)

    # Build multi_source_links for dashboard display
    multi_source_links = {}
    for category in categories:
        if category.is_multi_source:
            multi_links = BudgetService.get_multi_source_links(category.id)
            multi_source_links[category.id] = multi_links

    return render_template('budget/dashboard.html',
                         snapshot=snapshot,
                         budget_data=snapshot['categories'],
                         income_tiles=income_tiles,
                         quick_form=quick_form,
                         categories=categories,
                         income_sources=income_sources,
                         multi_source_links=multi_source_links,
                         current_month=year_month,
                         today=year_month.to_date().isoformat())


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

    # Get selected date (first day of month by default)
    selected_date = year_month.to_date().isoformat()

    return render_template('budget/expenses.html',
                         expenses=expenses_list,
                         categories=categories,
                         filter_form=filter_form,
                         current_month=year_month,
                         selected_date=selected_date,
                         today=selected_date)


@budget_bp.route('/expenses/add', methods=['GET', 'POST'])
@login_required
def add_expense():
    """Add new expense."""
    user_id = session['user_id']

    # Handle modal form submission (simple fields, 'note' instead of 'description')
    if request.method == 'POST' and 'date' in request.form and 'note' not in ExpenseForm.__dict__:
        try:
            from datetime import datetime
            from decimal import Decimal

            category_id = int(request.form.get('category_id', 0))
            amount_str = request.form.get('amount', '').replace(',', '.')
            note = request.form.get('note', '').strip()
            date_str = request.form.get('date', '')

            if not category_id or not amount_str or not date_str:
                flash('Заполните все обязательные поля', 'error')
                return redirect(url_for('budget.dashboard'))

            amount = Decimal(amount_str)
            date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()

            expense = BudgetService.add_expense(
                user_id=user_id,
                category_id=category_id,
                amount=amount,
                description=note,
                date_val=date_obj,
                currency='RUB'
            )
            flash('Расход добавлен', 'success')
            return redirect(url_for('budget.dashboard'))
        except Exception as e:
            flash(f'Ошибка при добавлении расхода: {str(e)}', 'error')
            return redirect(url_for('budget.dashboard'))

    # Handle regular form submission
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

    # Handle modal form submission (simple fields, 'note' instead of 'description')
    if request.method == 'POST' and 'note' in request.form:
        try:
            from datetime import datetime
            from decimal import Decimal

            category_id = int(request.form.get('category_id', 0))
            amount_str = request.form.get('amount', '').replace(',', '.')
            note = request.form.get('note', '').strip()
            date_str = request.form.get('date', '')

            if not category_id or not amount_str or not date_str:
                flash('Заполните все обязательные поля', 'error')
                return redirect(url_for('budget.expenses'))

            amount = Decimal(amount_str)
            date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()

            BudgetService.update_expense(
                expense_id=expense_id,
                user_id=user_id,
                category_id=category_id,
                amount=amount,
                description=note,
                date=date_obj,
                currency='RUB'
            )
            flash('Расход обновлен', 'success')
            return redirect(url_for('budget.expenses'))
        except Exception as e:
            flash(f'Ошибка при обновлении расхода: {str(e)}', 'error')
            return redirect(url_for('budget.expenses'))

    # Handle regular form submission
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
    income_sources = BudgetService.get_user_income_sources(user_id)
    
    # Build rules map for single-source categories
    rules_map = {}
    multi_source_links = {}
    
    for category in categories_list:
        if category.is_multi_source:
            # Get multi-source links for this category
            multi_links = BudgetService.get_multi_source_links(category.id)
            multi_source_links[category.id] = multi_links
        else:
            # Get single source rule for this category
            single_rule = BudgetService.get_category_single_source(category.id)
            if single_rule:
                rules_map[category.id] = single_rule.source_id
    
    return render_template('budget/categories.html',
                         categories=categories_list,
                         expense_categories=categories_list,  # Template expects this name
                         income_sources=income_sources,
                         rules_map=rules_map,
                         multi_source_links=multi_source_links,
                         today=datetime.date.today().isoformat())


@budget_bp.route('/modals/category/add', methods=['GET'])
@login_required
def category_add_modal():
    """Return category add modal content."""
    user_id = session['user_id']
    income_sources = IncomeSource.query.filter_by(user_id=user_id).all()
    return render_template('components/modals/category_add.html',
                         income_sources=income_sources)


@budget_bp.route('/categories/add', methods=['GET', 'POST'])
@login_required
def add_category():
    """Add new category."""
    user_id = session['user_id']
    
    if request.method == 'POST':
        # Handle modal form data
        name = request.form.get('name', '').strip()
        limit_type = request.form.get('limit_type', 'fixed')
        value = request.form.get('value', '0')
        is_multi_source = request.form.get('multi_source') == 'on'
        source_id = request.form.get('source_id')

        if not name:
            flash('Введите название категории', 'error')
            return redirect(url_for('budget.categories'))

        try:
            import json
            from app.core.extensions import db
            from app.modules.budget.models import CategoryRule, CategoryIncomeSource

            # Create category with multi-source flag
            category = BudgetService.create_category(
                user_id=user_id,
                name=name,
                limit_type=limit_type,
                value=float(value) if not is_multi_source else 0
            )

            # Flush to get category ID before adding links
            db.session.flush()

            # Set multi-source flag and process multi-source data
            if is_multi_source:
                category.is_multi_source = True

                # Process multi-source data from JSON
                sources_data_json = request.form.get('sources_data', '[]')
                try:
                    sources_data = json.loads(sources_data_json)
                except (json.JSONDecodeError, TypeError):
                    sources_data = []

                for source_data in sources_data:
                    source_id_multi = source_data.get('id')
                    source_name = source_data.get('name')
                    source_type = source_data.get('type', 'percent')
                    source_value = source_data.get('value', 0)

                    if source_id_multi and source_value > 0:
                        # Verify source belongs to user
                        source = IncomeSource.query.filter_by(id=source_id_multi, user_id=user_id).first()
                        if source:
                            cat_rule = CategoryRule(
                                category_id=category.id,
                                source_name=source.name,
                                percentage=float(source_value),
                                is_fixed=(source_type == 'fixed')
                            )
                            db.session.add(cat_rule)
            else:
                # Single source category - add link if source selected
                if source_id:
                    link = CategoryIncomeSource(
                        user_id=user_id,
                        category_id=category.id,
                        source_id=int(source_id),
                        limit_type=limit_type,
                        percentage=float(value) if limit_type == 'percent' else 100.0,
                        fixed_amount=float(value) if limit_type == 'fixed' else None
                    )
                    db.session.add(link)

            db.session.commit()

            flash('Категория создана', 'success')
            return redirect(url_for('budget.categories'))
            
        except Exception as e:
            flash(f'Ошибка при создании категории: {str(e)}', 'error')
            return redirect(url_for('budget.categories'))
    
    # GET request - show form
    form = CategoryForm()
    return render_template('budget/category_form.html', form=form, title='Добавить категорию')


@budget_bp.route('/modals/category/<int:category_id>/edit', methods=['GET'])
@login_required
def category_edit_modal(category_id):
    """Return category edit modal content."""
    from app.modules.budget.models import CategoryRule, CategoryIncomeSource
    user_id = session['user_id']
    category = Category.query.filter_by(id=category_id, user_id=user_id).first_or_404()
    income_sources = IncomeSource.query.filter_by(user_id=user_id).all()

    # Get existing rules for multi-source categories
    rules = CategoryRule.query.filter_by(category_id=category_id).all()
    rules_map = {rule.source_name: rule for rule in rules}

    # Get current source_id for single-source categories
    current_source_link = CategoryIncomeSource.query.filter_by(category_id=category_id).first()
    category.source_id = current_source_link.source_id if current_source_link else None

    return render_template('components/modals/category_edit.html',
                         category=category,
                         income_sources=income_sources,
                         rules_map=rules_map)


@budget_bp.route('/modals/category/<int:category_id>/sources', methods=['GET'])
@login_required
def category_sources_modal(category_id):
    """Return category sources management modal content."""
    from app.modules.budget.models import CategoryRule
    user_id = session['user_id']
    category = Category.query.filter_by(id=category_id, user_id=user_id).first_or_404()
    income_sources = IncomeSource.query.filter_by(user_id=user_id).all()

    # Get existing rules
    rules = CategoryRule.query.filter_by(category_id=category_id).all()

    response = make_response(render_template('components/modals/category_sources.html',
                         category=category,
                         income_sources=income_sources,
                         rules=rules))

    # Prevent browser caching of modal content to ensure fresh data
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'

    return response


@budget_bp.route('/categories/edit/<int:category_id>', methods=['GET', 'POST'])
@login_required
def edit_category(category_id):
    """Edit category."""
    user_id = session['user_id']
    category = Category.query.filter_by(id=category_id, user_id=user_id).first_or_404()

    # Check if AJAX request
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    if request.method == 'POST':
        try:
            from app.core.extensions import db
            from app.modules.budget.models import CategoryIncomeSource

            # Get form data
            name = request.form.get('name', '').strip()
            limit_type = request.form.get('limit_type', 'fixed')
            value = request.form.get('value', '0')
            is_multi_source = request.form.get('is_multi_source') == '1'
            source_id = request.form.get('source_id')

            if not name:
                if is_ajax:
                    return jsonify({'success': False, 'error': 'Введите название категории'})
                flash('Введите название категории', 'error')
                return redirect(url_for('budget.categories'))

            # Update basic category info
            category.name = name
            category.limit_type = limit_type
            category.is_multi_source = is_multi_source

            # Update value and source for non-multi-source categories
            if not is_multi_source:
                category.value = float(value) if value else 0

                # Update source link - remove all existing and create one
                if source_id:
                    # Remove existing links
                    CategoryIncomeSource.query.filter_by(category_id=category.id).delete()

                    # Create new link
                    link = CategoryIncomeSource(
                        user_id=user_id,
                        category_id=category.id,
                        source_id=int(source_id),
                        limit_type=limit_type,
                        percentage=float(value) if limit_type == 'percent' else 100.0,
                        fixed_amount=float(value) if limit_type == 'fixed' else None
                    )
                    db.session.add(link)
            else:
                category.value = 0

            db.session.commit()

            if is_ajax:
                return jsonify({
                    'success': True,
                    'message': 'Категория обновлена',
                    'category_id': category.id
                })

            flash('Категория обновлена', 'success')
            return redirect(url_for('budget.categories'))

        except Exception as e:
            if is_ajax:
                return jsonify({'success': False, 'error': f'Ошибка при обновлении категории: {str(e)}'})
            flash(f'Ошибка при обновлении категории: {str(e)}', 'error')
            return redirect(url_for('budget.categories'))

    # GET request - redirect to categories (no separate form page)
    return redirect(url_for('budget.categories'))


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
        date_input = request.form.get('date')  # Format: YYYY-MM-DD
        
        if source_name and amount and date_input:
            try:
                date_obj = datetime.datetime.strptime(date_input, '%Y-%m-%d').date()
                income = BudgetService.add_income(
                    user_id=user_id,
                    source_name=source_name,
                    amount=float(amount),
                    date=date_obj,
                    # Legacy fields for backward compatibility
                    year=date_obj.year,
                    month=date_obj.month,
                    currency='RUB'
                )
                flash('Доход добавлен', 'success')
                # Redirect to income page with the month of the added income
                income_year_month = YearMonth.from_date(date_obj)
                return redirect(url_for('budget.income', ym=str(income_year_month)))
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

    # Get selected date (first day of month by default)
    selected_date = year_month.to_date().isoformat()

    return render_template('budget/income.html',
                         income_list=income_list,
                         total_income=total_income,
                         current_month=year_month,
                         selected_date=selected_date,
                         today=selected_date)


@budget_bp.route('/income/add', methods=['GET', 'POST'])
@login_required
def add_income():
    """Add new income."""
    user_id = session['user_id']

    # Handle modal form submission (simple date field)
    if request.method == 'POST' and 'date' in request.form:
        try:
            from datetime import datetime
            from decimal import Decimal

            source_name = request.form.get('source_name', '').strip()
            amount_str = request.form.get('amount', '').replace(',', '.')
            date_str = request.form.get('date', '')

            if not source_name or not amount_str or not date_str:
                flash('Заполните все обязательные поля', 'error')
                return redirect(url_for('budget.dashboard'))

            amount = Decimal(amount_str)
            date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()

            income = BudgetService.add_income(
                user_id=user_id,
                source_name=source_name,
                amount=amount,
                date=date_obj,
                currency='RUB'
            )
            flash('Доход добавлен', 'success')
            return redirect(url_for('budget.dashboard'))
        except Exception as e:
            flash(f'Ошибка при добавлении дохода: {str(e)}', 'error')
            return redirect(url_for('budget.dashboard'))

    # Handle regular form submission (year/month fields)
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


@budget_bp.route('/sources/add', methods=['POST'])
@login_required
def sources_add():
    """Add new income source."""
    from app.core.extensions import db
    user_id = session['user_id']
    name = (request.form.get('name') or '').strip()
    is_default = 1 if request.form.get('is_default') == '1' else 0
    
    if not name:
        flash('Введите название источника', 'error')
        return redirect(url_for('budget.income'))
    
    try:
        # If setting as default, clear other defaults
        if is_default:
            IncomeSource.query.filter_by(user_id=user_id, is_default=True).update({'is_default': False})
        
        # Create new source
        source = IncomeSource(
            user_id=user_id,
            name=name,
            is_default=bool(is_default)
        )
        db.session.add(source)
        db.session.commit()
        flash('Источник добавлен', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Источник с таким названием уже существует', 'error')
    
    return redirect(url_for('budget.income'))


@budget_bp.route('/income/edit/<int:income_id>', methods=['GET', 'POST'])
@login_required
def edit_income(income_id):
    """Edit income."""
    user_id = session['user_id']
    income = Income.query.filter_by(id=income_id, user_id=user_id).first_or_404()
    
    if request.method == 'POST':
        # Handle modal form submission
        try:
            source_name = request.form.get('source_name')
            amount = Decimal(request.form.get('amount', '0'))
            date_input = request.form.get('date')  # Format: YYYY-MM-DD
            
            if date_input:
                from datetime import datetime
                date_obj = datetime.strptime(date_input, '%Y-%m-%d').date()
            else:
                # Fallback to existing date or construct from year/month
                date_obj = income.date or datetime(income.year, income.month, 1).date()
            
            BudgetService.update_income(
                income_id=income_id,
                user_id=user_id,
                source_name=source_name,
                amount=amount,
                date=date_obj,
                currency='RUB'
            )
            flash('Доход обновлен', 'success')
            # Redirect to income page with the month of the updated income
            income_year_month = YearMonth.from_date(date_obj)
            return redirect(url_for('budget.income', ym=str(income_year_month)))
        except Exception as e:
            flash(f'Ошибка при обновлении дохода: {str(e)}', 'error')
            return redirect(url_for('budget.income'))
    
    # GET request - render form page
    form = IncomeForm(obj=income)
    return render_template('budget/income_form.html', form=form, title='Редактировать доход')


@budget_bp.route('/income/delete/<int:income_id>', methods=['POST'])
@login_required
def delete_income(income_id):
    """Delete income."""
    user_id = session['user_id']
    
    if BudgetService.delete_income(income_id, user_id):
        flash('Доход удален', 'success')
    else:
        flash('Доход не найден', 'error')
    
    return redirect(url_for('budget.income'))


@budget_bp.route('/categories/<int:cat_id>/toggle-multi-source', methods=['POST'])
@login_required
def toggle_multi_source(cat_id):
    """Toggle multi-source mode for category."""
    user_id = session['user_id']
    
    try:
        # Find category
        category = Category.query.filter_by(id=cat_id, user_id=user_id).first()
        if not category:
            return jsonify({'error': 'Category not found'}), 404
        
        # Toggle multi-source flag
        category.is_multi_source = not category.is_multi_source
        
        from app.core.extensions import db
        db.session.commit()
        
        return jsonify({
            'success': True,
            'is_multi_source': category.is_multi_source,
            'message': 'Режим мультиисточников ' + ('включен' if category.is_multi_source else 'отключен')
        })
        
    except Exception as e:
        from app.core.extensions import db
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@budget_bp.route('/categories/<int:cat_id>/add-source', methods=['POST'])
@login_required
def add_source_to_category(cat_id):
    """Add income source to multi-source category."""
    from flask import jsonify
    from app.modules.budget.models import CategoryRule

    user_id = session['user_id']

    # Check if request is AJAX (from fetch/XMLHttpRequest)
    is_ajax = (
        request.headers.get('X-Requested-With') == 'XMLHttpRequest' or
        'application/json' in request.headers.get('Accept', '') or
        request.args.get('format') == 'json'
    )

    try:
        from app.core.extensions import db

        # Find category
        category = Category.query.filter_by(id=cat_id, user_id=user_id).first()
        if not category:
            if is_ajax:
                return jsonify({'success': False, 'error': 'Категория не найдена'}), 404
            flash('Категория не найдена', 'error')
            return redirect(url_for('budget.categories'))

        source_id = request.form.get('source_id')
        limit_type = request.form.get('limit_type', 'percent')
        percentage_value = request.form.get('value', type=float)

        if not source_id:
            if is_ajax:
                return jsonify({'success': False, 'error': 'Выберите источник дохода'}), 400
            flash('Выберите источник дохода', 'error')
            return redirect(url_for('budget.categories'))

        # Check if source exists and belongs to user
        source = IncomeSource.query.filter_by(id=source_id, user_id=user_id).first()
        if not source:
            if is_ajax:
                return jsonify({'success': False, 'error': 'Источник дохода не найден'}), 404
            flash('Источник дохода не найден', 'error')
            return redirect(url_for('budget.categories'))

        # Check if this source is already added to category
        existing = CategoryRule.query.filter_by(
            category_id=cat_id,
            source_name=source.name
        ).first()
        if existing:
            if is_ajax:
                return jsonify({'success': False, 'error': f'Источник "{source.name}" уже добавлен к категории'}), 400
            flash(f'Источник "{source.name}" уже добавлен к категории', 'error')
            return redirect(url_for('budget.categories'))

        # Validate percentage value
        if not percentage_value or percentage_value <= 0:
            if is_ajax:
                return jsonify({'success': False, 'error': 'Укажите корректное значение (больше 0)'}), 400
            flash('Укажите корректное значение (больше 0)', 'error')
            return redirect(url_for('budget.categories'))

        if limit_type == 'percent' and percentage_value > 100:
            if is_ajax:
                return jsonify({'success': False, 'error': 'Процент не может быть больше 100'}), 400
            flash('Процент не может быть больше 100', 'error')
            return redirect(url_for('budget.categories'))

        # Create CategoryRule
        cat_rule = CategoryRule(
            category_id=cat_id,
            source_name=source.name,
            percentage=percentage_value,
            is_fixed=(limit_type == 'fixed')
        )

        db.session.add(cat_rule)
        db.session.commit()

        # Invalidate cache
        from app.core.caching import CacheManager
        CacheManager.invalidate_budget_cache(user_id)

        flash_msg = f'Источник "{source.name}" добавлен к категории'
        if is_ajax:
            return jsonify({'success': True, 'message': flash_msg})

        flash(flash_msg, 'success')
        return redirect(url_for('budget.categories'))

    except Exception as e:
        from app.core.extensions import db
        db.session.rollback()
        error_msg = f'Ошибка при добавлении источника: {str(e)}'
        if is_ajax:
            return jsonify({'success': False, 'error': error_msg}), 500

        flash(error_msg, 'error')
        return redirect(url_for('budget.categories'))


@budget_bp.route('/categories/<int:cat_id>/update-source-percentage', methods=['POST'])
@login_required
def update_source_percentage(cat_id):
    """Update percentage for income source in multi-source category."""
    user_id = session['user_id']
    
    try:
        from app.core.extensions import db
        from app.modules.budget.models import CategoryRule
        
        # Find category
        category = Category.query.filter_by(id=cat_id, user_id=user_id).first()
        if not category:
            flash('Категория не найдена', 'error')
            return redirect(url_for('budget.categories'))
        
        source_id = request.form.get('source_id')
        percentage = request.form.get('percentage', type=float)
        
        if not source_id:
            flash('Источник не указан', 'error')
            return redirect(url_for('budget.categories'))
            
        if not percentage or percentage <= 0 or percentage > 100:
            flash('Укажите корректный процент (1-100)', 'error')
            return redirect(url_for('budget.categories'))
        
        # Find source to get its name
        source = IncomeSource.query.filter_by(id=source_id, user_id=user_id).first()
        if not source:
            flash('Источник дохода не найден', 'error')
            return redirect(url_for('budget.categories'))
        
        # Find and update CategoryRule
        cat_rule = CategoryRule.query.filter_by(
            category_id=cat_id, 
            source_name=source.name
        ).first()
        
        if not cat_rule:
            flash('Связь источника с категорией не найдена', 'error')
            return redirect(url_for('budget.categories'))
        
        cat_rule.percentage = percentage
        db.session.commit()
        
        flash(f'Процент для источника "{source.name}" обновлен до {percentage}%', 'success')
        
    except Exception as e:
        from app.core.extensions import db
        db.session.rollback()
        flash(f'Ошибка при обновлении процента: {str(e)}', 'error')
    
    return redirect(url_for('budget.categories'))


@budget_bp.route('/categories/<int:cat_id>/remove-source/<int:source_id>', methods=['POST'])
@login_required
def remove_source_from_category(cat_id, source_id):
    """Remove income source from multi-source category."""
    user_id = session['user_id']
    
    try:
        from app.core.extensions import db
        from app.modules.budget.models import CategoryRule
        
        # Find category
        category = Category.query.filter_by(id=cat_id, user_id=user_id).first()
        if not category:
            flash('Категория не найдена', 'error')
            return redirect(url_for('budget.categories'))
        
        # Find source to get its name
        source = IncomeSource.query.filter_by(id=source_id, user_id=user_id).first()
        if not source:
            flash('Источник дохода не найден', 'error')
            return redirect(url_for('budget.categories'))
        
        # Find and remove CategoryRule
        cat_rule = CategoryRule.query.filter_by(
            category_id=cat_id, 
            source_name=source.name
        ).first()
        
        if not cat_rule:
            flash('Связь источника с категорией не найдена', 'error')
            return redirect(url_for('budget.categories'))
        
        db.session.delete(cat_rule)
        db.session.commit()
        
        flash(f'Источник "{source.name}" удален из категории', 'success')
        
    except Exception as e:
        from app.core.extensions import db
        db.session.rollback()
        flash(f'Ошибка при удалении источника: {str(e)}', 'error')
    
    return redirect(url_for('budget.categories'))


@budget_bp.route('/income-sources/add', methods=['POST'])
@login_required
def add_income_source():
    """Add new income source."""
    from .models import IncomeSource
    from app.core.extensions import db
    from flask import current_app
    from sqlalchemy import func
    
    user_id = session['user_id']
    name = request.form.get('name', '').strip()
    
    if not name:
        flash('Название источника дохода не может быть пустым', 'error')
        return redirect(url_for('budget.categories'))
    
    # Check if source with this name already exists (case-insensitive)
    existing_source = IncomeSource.query.filter(
        IncomeSource.user_id == user_id,
        func.lower(IncomeSource.name) == func.lower(name)
    ).first()
    if existing_source:
        flash(f'Источник дохода с названием "{name}" уже существует', 'error')
        return redirect(url_for('budget.categories'))
    
    # Create new income source
    try:
        new_source = IncomeSource(user_id=user_id, name=name)
        db.session.add(new_source)
        db.session.commit()
        flash(f'Источник дохода "{name}" создан', 'success')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Error creating income source for user {user_id}: {str(e)}')
        flash('Ошибка при создании источника дохода', 'error')
    
    return redirect(url_for('budget.categories'))


@budget_bp.route('/income-sources/delete/<int:source_id>', methods=['POST'])
@login_required
def delete_income_source(source_id):
    """Delete income source."""
    from .models import IncomeSource, CategoryRule, Income
    from app.core.extensions import db
    from flask import current_app
    
    user_id = session['user_id']
    
    try:
        # Find the source to delete
        source = IncomeSource.query.filter_by(id=source_id, user_id=user_id).first()
        
        if not source:
            flash('Источник дохода не найден', 'error')
            return redirect(url_for('budget.categories'))
        
        source_name = source.name
        
        # Delete all related data in transaction
        
        # 1. Delete category_rules (links by source_name)
        CategoryRule.query.filter_by(source_name=source_name).delete()
        
        # 2. Delete source_category_rules (links by source_id)
        db.session.execute(
            db.text("DELETE FROM source_category_rules WHERE source_id = :source_id"),
            {"source_id": source_id}
        )
        
        # 3. Delete category_income_sources (links by source_id)
        db.session.execute(
            db.text("DELETE FROM category_income_sources WHERE source_id = :source_id"),
            {"source_id": source_id}
        )
        
        # 4. Delete related income records (by source_name)
        Income.query.filter_by(user_id=user_id, source_name=source_name).delete()
        
        # Delete the source itself
        db.session.delete(source)
        db.session.commit()
        
        # Invalidate cache
        from app.core.caching import CacheManager
        CacheManager.invalidate_budget_cache(user_id)
        
        current_app.logger.info(f'Deleted income source {source_name} for user {user_id}')
        flash(f'Источник дохода "{source_name}" удален', 'success')
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Error deleting income source {source_id} for user {user_id}: {str(e)}')
        flash('Ошибка при удалении источника дохода', 'error')
    
    return redirect(url_for('budget.categories'))


# Modal routes for expenses
@budget_bp.route('/modals/expense/add')
@login_required
@monitor_modal_performance('expense_add')
def expense_add_modal():
    """Return expense add modal content."""
    user_id = session['user_id']
    categories = BudgetService.get_user_categories(user_id)
    
    # Get month data for form action
    ym_param = request.args.get('month')
    try:
        month_data = parse_year_month(ym_param) if ym_param else YearMonth.current()
    except ValueError:
        month_data = YearMonth.current()
    
    return render_template('components/modals/expense_add.html',
                         categories=categories,
                         month_data=month_data,
                         today=month_data.to_date().isoformat())


@budget_bp.route('/modals/expense/<int:expense_id>/edit')
@login_required
@monitor_modal_performance('expense_edit')
def expense_edit_modal(expense_id):
    """Return expense edit modal content."""
    user_id = session['user_id']
    expense = Expense.query.filter_by(id=expense_id, user_id=user_id).first_or_404()
    categories = BudgetService.get_user_categories(user_id)
    
    return render_template('components/modals/expense_edit.html', 
                         expense=expense,
                         categories=categories)


# Modal routes for income
@budget_bp.route('/modals/income/add')
@login_required
@monitor_modal_performance('income_add')
def income_add_modal():
    """Return income add modal content."""
    user_id = session['user_id']
    
    # Get month data for form action
    ym_param = request.args.get('month')
    try:
        month_data = parse_year_month(ym_param) if ym_param else YearMonth.current()
    except ValueError:
        month_data = YearMonth.current()
    
    return render_template('components/modals/income_add.html',
                         month_data=month_data,
                         today=month_data.to_date().isoformat())


@budget_bp.route('/category-rules/<int:rule_id>/delete', methods=['POST'])
@login_required
def delete_category_rule(rule_id):
    """Delete a category rule."""
    from app.modules.budget.models import CategoryRule
    from app.core.extensions import db

    user_id = session['user_id']
    category_id = request.form.get('category_id')

    # Check if request is AJAX
    is_ajax = (
        request.headers.get('X-Requested-With') == 'XMLHttpRequest' or
        'application/json' in request.headers.get('Accept', '')
    )

    rule = CategoryRule.query.filter_by(id=rule_id).first_or_404()

    # Verify category belongs to user
    category = Category.query.filter_by(id=rule.category_id, user_id=user_id).first_or_404()

    source_name = rule.source_name
    db.session.delete(rule)
    db.session.commit()

    # Invalidate cache
    from app.core.caching import CacheManager
    CacheManager.invalidate_budget_cache(user_id)

    if is_ajax:
        return jsonify({
            'success': True,
            'message': f'Источник "{source_name}" удален',
            'category_id': category.id
        })

    flash('Источник удален', 'success')
    return redirect(url_for('budget.categories'))


@budget_bp.route('/modals/income/<int:income_id>/edit')
@login_required
@monitor_modal_performance('income_edit')
def income_edit_modal(income_id):
    """Return income edit modal content."""
    user_id = session['user_id']
    income = Income.query.filter_by(id=income_id, user_id=user_id).first_or_404()

    return render_template('components/modals/income_edit.html',
                         income=income)