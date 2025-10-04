"""Budget API endpoints."""
from flask import request, session, current_app
from flask_login import login_required
from app.core.time import YearMonth, parse_year_month
from app.modules.budget.service import BudgetService
from app.modules.budget.models import Expense, Category, Income
from .schemas import APIResponse, ExpenseSchema, CategorySchema, IncomeSchema, BudgetSnapshotSchema, RequestValidator
from . import api_v1_bp


@api_v1_bp.route('/budget/summary')
@login_required
def budget_summary():
    """Get budget summary for month."""
    user_id = current_user.id
    
    # Get year-month parameter
    ym_param = request.args.get('ym')
    if ym_param:
        year_month, error = RequestValidator.validate_year_month(ym_param)
        if error:
            return APIResponse.error(f"Invalid year-month: {error}"), 400
    else:
        year_month = YearMonth.current()
    
    try:
        snapshot = BudgetService.calculate_month_snapshot(user_id, year_month)
        data = BudgetSnapshotSchema.serialize(snapshot)
        return APIResponse.success(data)
    except Exception as e:
        current_app.logger.error(f"Error getting budget summary: {e}")
        return APIResponse.error("Failed to get budget summary"), 500


@api_v1_bp.route('/expenses')
@login_required
def get_expenses():
    """Get expenses for user."""
    user_id = current_user.id
    
    # Get filters
    ym_param = request.args.get('ym')
    category_id = request.args.get('category_id', type=int)
    limit = request.args.get('limit', 50, type=int)
    offset = request.args.get('offset', 0, type=int)
    
    # Validate year-month
    if ym_param:
        year_month, error = RequestValidator.validate_year_month(ym_param)
        if error:
            return APIResponse.error(f"Invalid year-month: {error}"), 400
    else:
        year_month = YearMonth.current()
    
    try:
        # Get expenses for month
        expenses = BudgetService.get_expenses_for_month(user_id, year_month)
        
        # Filter by category if specified
        if category_id:
            expenses = [exp for exp in expenses if exp.category_id == category_id]
        
        # Apply pagination
        total_count = len(expenses)
        expenses = expenses[offset:offset + limit]
        
        data = {
            'expenses': ExpenseSchema.serialize_list(expenses),
            'pagination': {
                'total': total_count,
                'limit': limit,
                'offset': offset,
                'has_more': offset + limit < total_count
            },
            'filters': {
                'year_month': str(year_month),
                'category_id': category_id
            }
        }
        
        return APIResponse.success(data)
    except Exception as e:
        current_app.logger.error(f"Error getting expenses: {e}")
        return APIResponse.error("Failed to get expenses"), 500


@api_v1_bp.route('/expenses', methods=['POST'])
@login_required
def create_expense():
    """Create new expense."""
    user_id = current_user.id
    
    try:
        data = request.get_json()
        if not data:
            return APIResponse.error("No data provided"), 400
        
        # Validate data
        validated_data = RequestValidator.validate_expense_create(data)
        
        # Create expense
        expense = BudgetService.add_expense(
            user_id=user_id,
            category_id=validated_data['category_id'],
            amount=validated_data['amount'],
            description=validated_data.get('description'),
            date_val=validated_data['date'],
            currency=validated_data['currency']
        )
        
        return APIResponse.success(
            ExpenseSchema.serialize(expense),
            "Expense created successfully"
        ), 201
        
    except ValueError as e:
        return APIResponse.error(str(e)), 400
    except Exception as e:
        current_app.logger.error(f"Error creating expense: {e}")
        return APIResponse.error("Failed to create expense"), 500


@api_v1_bp.route('/expenses/<int:expense_id>', methods=['PUT'])
@login_required
def update_expense(expense_id):
    """Update expense."""
    user_id = current_user.id
    
    try:
        data = request.get_json()
        if not data:
            return APIResponse.error("No data provided"), 400
        
        # Validate data
        validated_data = RequestValidator.validate_expense_create(data)
        
        # Update expense
        expense = BudgetService.update_expense(
            expense_id=expense_id,
            user_id=user_id,
            **validated_data
        )
        
        if not expense:
            return APIResponse.error("Expense not found"), 404
        
        return APIResponse.success(
            ExpenseSchema.serialize(expense),
            "Expense updated successfully"
        )
        
    except ValueError as e:
        return APIResponse.error(str(e)), 400
    except Exception as e:
        current_app.logger.error(f"Error updating expense: {e}")
        return APIResponse.error("Failed to update expense"), 500


@api_v1_bp.route('/expenses/<int:expense_id>', methods=['DELETE'])
@login_required
def delete_expense(expense_id):
    """Delete expense."""
    user_id = current_user.id
    
    try:
        success = BudgetService.delete_expense(expense_id, user_id)
        
        if not success:
            return APIResponse.error("Expense not found"), 404
        
        return APIResponse.success(message="Expense deleted successfully")
        
    except Exception as e:
        current_app.logger.error(f"Error deleting expense: {e}")
        return APIResponse.error("Failed to delete expense"), 500


@api_v1_bp.route('/categories')
@login_required
def get_categories():
    """Get categories for user."""
    user_id = current_user.id
    
    try:
        categories = BudgetService.get_user_categories(user_id)
        data = CategorySchema.serialize_list(categories)
        return APIResponse.success(data)
    except Exception as e:
        current_app.logger.error(f"Error getting categories: {e}")
        return APIResponse.error("Failed to get categories"), 500


@api_v1_bp.route('/categories', methods=['POST'])
@login_required
def create_category():
    """Create new category."""
    user_id = current_user.id
    
    try:
        data = request.get_json()
        if not data:
            return APIResponse.error("No data provided"), 400
        
        # Validate data
        validated_data = RequestValidator.validate_category_create(data)
        
        # Create category
        category = BudgetService.create_category(
            user_id=user_id,
            name=validated_data['name'],
            limit_type=validated_data['limit_type'],
            value=validated_data['value']
        )
        
        return APIResponse.success(
            CategorySchema.serialize(category),
            "Category created successfully"
        ), 201
        
    except ValueError as e:
        return APIResponse.error(str(e)), 400
    except Exception as e:
        current_app.logger.error(f"Error creating category: {e}")
        return APIResponse.error("Failed to create category"), 500


@api_v1_bp.route('/income')
@login_required
def get_income():
    """Get income for user."""
    user_id = current_user.id
    
    # Get year-month parameter
    ym_param = request.args.get('ym')
    if ym_param:
        year_month, error = RequestValidator.validate_year_month(ym_param)
        if error:
            return APIResponse.error(f"Invalid year-month: {error}"), 400
    else:
        year_month = YearMonth.current()
    
    try:
        income_list = BudgetService.get_income_for_month(user_id, year_month)
        total_income = BudgetService.get_total_income_for_month(user_id, year_month)
        
        data = {
            'income': IncomeSchema.serialize_list(income_list),
            'total': {
                'amount': float(total_income.amount),
                'currency': total_income.currency,
                'formatted': total_income.format()
            },
            'year_month': str(year_month)
        }
        
        return APIResponse.success(data)
    except Exception as e:
        current_app.logger.error(f"Error getting income: {e}")
        return APIResponse.error("Failed to get income"), 500


@api_v1_bp.route('/income', methods=['POST'])
@login_required
def create_income():
    """Create or update income."""
    user_id = current_user.id
    
    try:
        data = request.get_json()
        if not data:
            return APIResponse.error("No data provided"), 400
        
        # Validate data
        validated_data = RequestValidator.validate_income_create(data)
        
        # Create/update income - use date if available, fallback to year/month
        if 'date' in validated_data:
            income = BudgetService.add_income(
                user_id=user_id,
                source_name=validated_data['source_name'],
                amount=validated_data['amount'],
                date=validated_data['date'],
                currency=validated_data['currency']
            )
        else:
            # Legacy year/month support
            from datetime import date
            income_date = date(validated_data['year'], validated_data['month'], 1)
            income = BudgetService.add_income(
                user_id=user_id,
                source_name=validated_data['source_name'],
                amount=validated_data['amount'],
                date=income_date,
                currency=validated_data['currency']
            )
        
        return APIResponse.success(
            IncomeSchema.serialize(income),
            "Income saved successfully"
        ), 201
        
    except ValueError as e:
        return APIResponse.error(str(e)), 400
    except Exception as e:
        current_app.logger.error(f"Error saving income: {e}")
        return APIResponse.error("Failed to save income"), 500


@api_v1_bp.route('/income-sources')
@login_required
def get_income_sources():
    """Get income sources for current user."""
    from app.modules.budget.models import IncomeSource
    from app.core.extensions import db

    user_id = current_user.id

    try:
        sources = db.session.query(IncomeSource).filter_by(user_id=user_id).all()

        return APIResponse.success({
            'sources': [
                {
                    'id': str(source.id),
                    'name': source.name
                }
                for source in sources
            ]
        })
    except Exception as e:
        current_app.logger.error(f"Error getting income sources: {e}")
        return APIResponse.error("Failed to get income sources"), 500