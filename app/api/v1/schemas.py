"""API v1 schemas for request/response validation."""
from datetime import datetime, date
from typing import Dict, List, Optional, Any
from decimal import Decimal


class APIResponse:
    """Standard API response format."""
    
    @staticmethod
    def success(data: Any = None, message: str = None) -> Dict:
        """Create success response."""
        response = {
            'success': True,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        if data is not None:
            response['data'] = data
        
        if message:
            response['message'] = message
        
        return response
    
    @staticmethod
    def error(message: str, code: str = None, details: Any = None) -> Dict:
        """Create error response."""
        response = {
            'success': False,
            'error': {
                'message': message,
                'timestamp': datetime.utcnow().isoformat()
            }
        }
        
        if code:
            response['error']['code'] = code
        
        if details:
            response['error']['details'] = details
        
        return response


class ExpenseSchema:
    """Expense serialization schema."""
    
    @staticmethod
    def serialize(expense) -> Dict:
        """Serialize expense to dict."""
        return {
            'id': expense.id,
            'category_id': expense.category_id,
            'category_name': expense.category.name if expense.category else None,
            'amount': float(expense.amount),
            'currency': expense.currency,
            'description': expense.description,
            'date': expense.date.isoformat(),
            'created_at': expense.created_at.isoformat()
        }
    
    @staticmethod
    def serialize_list(expenses: List) -> List[Dict]:
        """Serialize list of expenses."""
        return [ExpenseSchema.serialize(expense) for expense in expenses]


class CategorySchema:
    """Category serialization schema."""
    
    @staticmethod
    def serialize(category) -> Dict:
        """Serialize category to dict."""
        return {
            'id': category.id,
            'name': category.name,
            'limit_type': category.limit_type,
            'value': float(category.value),
            'is_multi_source': category.is_multi_source,
            'created_at': category.created_at.isoformat()
        }
    
    @staticmethod
    def serialize_list(categories: List) -> List[Dict]:
        """Serialize list of categories."""
        return [CategorySchema.serialize(category) for category in categories]


class IncomeSchema:
    """Income serialization schema."""
    
    @staticmethod
    def serialize(income) -> Dict:
        """Serialize income to dict."""
        return {
            'id': income.id,
            'source_name': income.source_name,
            'amount': float(income.amount),
            'currency': income.currency,
            'year': income.year,
            'month': income.month,
            'year_month': f"{income.year}-{income.month:02d}",
            'created_at': income.created_at.isoformat()
        }
    
    @staticmethod
    def serialize_list(incomes: List) -> List[Dict]:
        """Serialize list of incomes."""
        return [IncomeSchema.serialize(income) for income in incomes]


class GoalSchema:
    """Savings goal serialization schema."""
    
    @staticmethod
    def serialize(goal) -> Dict:
        """Serialize goal to dict."""
        return {
            'id': goal.id,
            'title': goal.title,
            'description': goal.description,
            'target_amount': float(goal.target_amount),
            'current_amount': float(goal.current_amount),
            'currency': goal.currency,
            'target_date': goal.target_date.isoformat() if goal.target_date else None,
            'progress_percentage': float(goal.progress_percentage),
            'completed': goal.completed,
            'completed_at': goal.completed_at.isoformat() if goal.completed_at else None,
            'created_at': goal.created_at.isoformat()
        }
    
    @staticmethod
    def serialize_list(goals: List) -> List[Dict]:
        """Serialize list of goals."""
        return [GoalSchema.serialize(goal) for goal in goals]


class BudgetSnapshotSchema:
    """Budget snapshot serialization schema."""
    
    @staticmethod
    def serialize(snapshot: Dict) -> Dict:
        """Serialize budget snapshot."""
        return {
            'year_month': str(snapshot['year_month']),
            'total_income': {
                'amount': float(snapshot['total_income'].amount),
                'currency': snapshot['total_income'].currency,
                'formatted': snapshot['total_income'].format()
            },
            'total_spent': {
                'amount': float(snapshot['total_spent'].amount),
                'currency': snapshot['total_spent'].currency,
                'formatted': snapshot['total_spent'].format()
            },
            'total_remaining': {
                'amount': float(snapshot['total_remaining'].amount),
                'currency': snapshot['total_remaining'].currency,
                'formatted': snapshot['total_remaining'].format()
            },
            'categories': [
                {
                    'category': CategorySchema.serialize(cat_summary['category']),
                    'spent': {
                        'amount': float(cat_summary['spent'].amount),
                        'currency': cat_summary['spent'].currency,
                        'formatted': cat_summary['spent'].format()
                    },
                    'limit': {
                        'amount': float(cat_summary['limit'].amount),
                        'currency': cat_summary['limit'].currency,
                        'formatted': cat_summary['limit'].format()
                    },
                    'remaining': {
                        'amount': float(cat_summary['remaining'].amount),
                        'currency': cat_summary['remaining'].currency,
                        'formatted': cat_summary['remaining'].format()
                    },
                    'percentage_used': float(cat_summary['percentage_used']),
                    'expenses_count': len(cat_summary['expenses'])
                }
                for cat_summary in snapshot['categories']
            ]
        }


class UserSchema:
    """User serialization schema."""
    
    @staticmethod
    def serialize(user) -> Dict:
        """Serialize user to dict (safe for API)."""
        return {
            'id': user.id,
            'name': user.name,
            'display_name': user.display_name,
            'auth_type': user.auth_type,
            'theme': user.theme,
            'currency': user.currency,
            'timezone': user.timezone,
            'locale': user.locale,
            'is_telegram_user': user.is_telegram_user,
            'created_at': user.created_at.isoformat() if user.created_at else None
        }


# Request validation helpers
class RequestValidator:
    """Request data validation."""
    
    @staticmethod
    def validate_expense_create(data: Dict) -> Dict:
        """Validate expense creation data."""
        from app.modules.budget.schemas import ExpenseData
        return ExpenseData.validate(data)
    
    @staticmethod
    def validate_category_create(data: Dict) -> Dict:
        """Validate category creation data."""
        from app.modules.budget.schemas import CategoryData
        return CategoryData.validate(data)
    
    @staticmethod
    def validate_income_create(data: Dict) -> Dict:
        """Validate income creation data."""
        from app.modules.budget.schemas import IncomeData
        return IncomeData.validate(data)
    
    @staticmethod
    def validate_goal_create(data: Dict) -> Dict:
        """Validate goal creation data."""
        from app.modules.goals.schemas import SavingsGoalData
        return SavingsGoalData.validate(data)
    
    @staticmethod
    def validate_year_month(ym_string: str) -> tuple:
        """Validate and parse year-month string."""
        from app.core.time import parse_year_month
        try:
            year_month = parse_year_month(ym_string)
            return year_month, None
        except ValueError as e:
            return None, str(e)