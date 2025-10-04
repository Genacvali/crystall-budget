"""Goals API endpoints."""
from flask import request, session, current_app
from flask_login import login_required
from app.modules.goals.service import GoalsService, SharedBudgetService
from app.modules.goals.models import SavingsGoal, SharedBudget
from .schemas import APIResponse, GoalSchema, RequestValidator
from . import api_v1_bp


@api_v1_bp.route('/goals')
@login_required
def get_goals():
    """Get savings goals for user."""
    user_id = current_user.id
    
    try:
        goals = GoalsService.get_user_goals(user_id)
        statistics = GoalsService.get_goal_statistics(user_id)
        
        data = {
            'goals': GoalSchema.serialize_list(goals),
            'statistics': {
                'total_goals': statistics['total_goals'],
                'completed_goals': statistics['completed_goals'],
                'active_goals': statistics['active_goals'],
                'total_target': {
                    'amount': float(statistics['total_target'].amount),
                    'currency': statistics['total_target'].currency,
                    'formatted': statistics['total_target'].format()
                },
                'total_saved': {
                    'amount': float(statistics['total_saved'].amount),
                    'currency': statistics['total_saved'].currency,
                    'formatted': statistics['total_saved'].format()
                },
                'overall_progress': float(statistics['overall_progress'])
            }
        }
        
        return APIResponse.success(data)
    except Exception as e:
        current_app.logger.error(f"Error getting goals: {e}")
        return APIResponse.error("Failed to get goals"), 500


@api_v1_bp.route('/goals', methods=['POST'])
@login_required
def create_goal():
    """Create new savings goal."""
    user_id = current_user.id
    
    try:
        data = request.get_json()
        if not data:
            return APIResponse.error("No data provided"), 400
        
        # Validate data
        validated_data = RequestValidator.validate_goal_create(data)
        
        # Create goal
        goal = GoalsService.create_goal(
            user_id=user_id,
            title=validated_data['title'],
            target_amount=validated_data['target_amount'],
            description=validated_data.get('description'),
            target_date=validated_data.get('target_date'),
            currency=validated_data['currency']
        )
        
        return APIResponse.success(
            GoalSchema.serialize(goal),
            "Goal created successfully"
        ), 201
        
    except ValueError as e:
        return APIResponse.error(str(e)), 400
    except Exception as e:
        current_app.logger.error(f"Error creating goal: {e}")
        return APIResponse.error("Failed to create goal"), 500


@api_v1_bp.route('/goals/<int:goal_id>', methods=['PUT'])
@login_required
def update_goal(goal_id):
    """Update savings goal."""
    user_id = current_user.id
    
    try:
        data = request.get_json()
        if not data:
            return APIResponse.error("No data provided"), 400
        
        # Validate data
        validated_data = RequestValidator.validate_goal_create(data)
        
        # Update goal
        goal = GoalsService.update_goal(
            goal_id=goal_id,
            user_id=user_id,
            **validated_data
        )
        
        if not goal:
            return APIResponse.error("Goal not found"), 404
        
        return APIResponse.success(
            GoalSchema.serialize(goal),
            "Goal updated successfully"
        )
        
    except ValueError as e:
        return APIResponse.error(str(e)), 400
    except Exception as e:
        current_app.logger.error(f"Error updating goal: {e}")
        return APIResponse.error("Failed to update goal"), 500


@api_v1_bp.route('/goals/<int:goal_id>', methods=['DELETE'])
@login_required
def delete_goal(goal_id):
    """Delete savings goal."""
    user_id = current_user.id
    
    try:
        success = GoalsService.delete_goal(goal_id, user_id)
        
        if not success:
            return APIResponse.error("Goal not found"), 404
        
        return APIResponse.success(message="Goal deleted successfully")
        
    except Exception as e:
        current_app.logger.error(f"Error deleting goal: {e}")
        return APIResponse.error("Failed to delete goal"), 500


@api_v1_bp.route('/goals/<int:goal_id>/progress', methods=['POST'])
@login_required
def add_goal_progress(goal_id):
    """Add progress to savings goal."""
    user_id = current_user.id
    
    try:
        data = request.get_json()
        if not data:
            return APIResponse.error("No data provided"), 400
        
        # Validate amount
        if 'amount' not in data:
            return APIResponse.error("Amount is required"), 400
        
        try:
            amount = float(data['amount'])
            if amount <= 0:
                return APIResponse.error("Amount must be positive"), 400
        except (ValueError, TypeError):
            return APIResponse.error("Invalid amount"), 400
        
        # Add progress
        goal = GoalsService.add_progress(goal_id, user_id, amount)
        
        if not goal:
            return APIResponse.error("Goal not found"), 404
        
        message = "Progress added successfully"
        if goal.completed:
            message += " - Goal completed! 🎉"
        
        return APIResponse.success(
            GoalSchema.serialize(goal),
            message
        )
        
    except Exception as e:
        current_app.logger.error(f"Error adding goal progress: {e}")
        return APIResponse.error("Failed to add progress"), 500


@api_v1_bp.route('/shared-budgets')
@login_required
def get_shared_budgets():
    """Get shared budgets for user."""
    user_id = current_user.id
    
    try:
        budgets = SharedBudgetService.get_user_shared_budgets(user_id)
        
        data = []
        for budget in budgets:
            budget_data = budget.to_dict()
            
            # Get user's role in this budget
            members = SharedBudgetService.get_budget_members(budget.id)
            user_member = next((m for m in members if m.user_id == user_id), None)
            budget_data['user_role'] = user_member.role if user_member else None
            
            data.append(budget_data)
        
        return APIResponse.success(data)
    except Exception as e:
        current_app.logger.error(f"Error getting shared budgets: {e}")
        return APIResponse.error("Failed to get shared budgets"), 500


@api_v1_bp.route('/shared-budgets', methods=['POST'])
@login_required
def create_shared_budget():
    """Create new shared budget."""
    user_id = current_user.id
    
    try:
        data = request.get_json()
        if not data:
            return APIResponse.error("No data provided"), 400
        
        # Validate required fields
        if 'name' not in data:
            return APIResponse.error("Budget name is required"), 400
        
        name = str(data['name']).strip()
        if not (2 <= len(name) <= 200):
            return APIResponse.error("Budget name must be 2-200 characters"), 400
        
        description = data.get('description', '').strip()
        if len(description) > 1000:
            return APIResponse.error("Description too long"), 400
        
        # Create shared budget
        budget = SharedBudgetService.create_shared_budget(
            user_id=user_id,
            name=name,
            description=description or None
        )
        
        budget_data = budget.to_dict()
        budget_data['user_role'] = 'owner'
        
        return APIResponse.success(
            budget_data,
            f"Shared budget created. Invitation code: {budget.invitation_code}"
        ), 201
        
    except Exception as e:
        current_app.logger.error(f"Error creating shared budget: {e}")
        return APIResponse.error("Failed to create shared budget"), 500


@api_v1_bp.route('/shared-budgets/join', methods=['POST'])
@login_required
def join_shared_budget():
    """Join shared budget by invitation code."""
    user_id = current_user.id
    
    try:
        data = request.get_json()
        if not data:
            return APIResponse.error("No data provided"), 400
        
        # Validate invitation code
        if 'invitation_code' not in data:
            return APIResponse.error("Invitation code is required"), 400
        
        invitation_code = str(data['invitation_code']).strip().upper()
        if len(invitation_code) != 8:
            return APIResponse.error("Invalid invitation code"), 400
        
        # Join budget
        budget = SharedBudgetService.join_shared_budget(user_id, invitation_code)
        
        if not budget:
            return APIResponse.error("Invalid invitation code"), 404
        
        budget_data = budget.to_dict()
        budget_data['user_role'] = 'member'
        
        return APIResponse.success(
            budget_data,
            f"Successfully joined budget: {budget.name}"
        )
        
    except Exception as e:
        current_app.logger.error(f"Error joining shared budget: {e}")
        return APIResponse.error("Failed to join shared budget"), 500


@api_v1_bp.route('/shared-budgets/<int:budget_id>')
@login_required
def get_shared_budget_detail(budget_id):
    """Get shared budget details."""
    user_id = current_user.id
    
    try:
        summary = SharedBudgetService.get_budget_summary(budget_id, user_id)
        
        if not summary:
            return APIResponse.error("Budget not found or access denied"), 404
        
        # Serialize budget data
        budget_data = summary['budget'].to_dict()
        budget_data['user_role'] = summary['user_role']
        budget_data['can_manage'] = summary['can_manage']
        
        # Add member information
        members_data = []
        for member in summary['members']:
            member_data = member.to_dict()
            # TODO: Add user name from User model
            members_data.append(member_data)
        
        budget_data['members'] = members_data
        
        return APIResponse.success(budget_data)
        
    except Exception as e:
        current_app.logger.error(f"Error getting shared budget detail: {e}")
        return APIResponse.error("Failed to get budget details"), 500