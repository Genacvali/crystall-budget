"""Goals service layer."""
from typing import List, Optional
from decimal import Decimal
from datetime import datetime, date
from flask import current_app
from app.core.extensions import db
from app.core.money import Money
from app.core.caching import CacheManager
from .models import SavingsGoal, SharedBudget, SharedBudgetMember
import secrets
import string


class GoalsService:
    """Savings goals business logic service."""
    
    @staticmethod
    def get_user_goals(user_id: int) -> List[SavingsGoal]:
        """Get all savings goals for user."""
        return SavingsGoal.query.filter_by(user_id=user_id).order_by(SavingsGoal.created_at.desc()).all()
    
    @staticmethod
    def create_goal(user_id: int, title: str, target_amount: Decimal, 
                   description: str = None, target_date: date = None, currency: str = 'RUB') -> SavingsGoal:
        """Create new savings goal."""
        goal = SavingsGoal(
            user_id=user_id,
            title=title,
            description=description,
            target_amount=target_amount,
            currency=currency,
            target_date=target_date
        )
        db.session.add(goal)
        db.session.commit()
        
        # Invalidate cache
        CacheManager.invalidate_goals_cache(user_id)
        
        current_app.logger.info(f'Created savings goal {title} for user {user_id}')
        return goal
    
    @staticmethod
    def update_goal(goal_id: int, user_id: int, **kwargs) -> Optional[SavingsGoal]:
        """Update savings goal."""
        goal = SavingsGoal.query.filter_by(id=goal_id, user_id=user_id).first()
        if not goal:
            return None
        
        for key, value in kwargs.items():
            if hasattr(goal, key):
                setattr(goal, key, value)
        
        db.session.commit()
        
        # Invalidate cache
        CacheManager.invalidate_goals_cache(user_id)
        
        current_app.logger.info(f'Updated savings goal {goal_id} for user {user_id}')
        return goal
    
    @staticmethod
    def delete_goal(goal_id: int, user_id: int) -> bool:
        """Delete savings goal."""
        goal = SavingsGoal.query.filter_by(id=goal_id, user_id=user_id).first()
        if not goal:
            return False
        
        db.session.delete(goal)
        db.session.commit()
        
        # Invalidate cache
        CacheManager.invalidate_goals_cache(user_id)
        
        current_app.logger.info(f'Deleted savings goal {goal_id} for user {user_id}')
        return True
    
    @staticmethod
    def add_progress(goal_id: int, user_id: int, amount: Decimal) -> Optional[SavingsGoal]:
        """Add progress to savings goal."""
        goal = SavingsGoal.query.filter_by(id=goal_id, user_id=user_id).first()
        if not goal:
            return None
        
        old_completed = goal.completed
        goal.add_progress(amount)
        
        # Check if goal was just completed
        if not old_completed and goal.completed:
            current_app.logger.info(f'Savings goal {goal_id} completed for user {user_id}!')
            # TODO: Send notification
        
        # Invalidate cache
        CacheManager.invalidate_goals_cache(user_id)
        
        current_app.logger.info(f'Added {amount} progress to goal {goal_id} for user {user_id}')
        return goal
    
    @staticmethod
    def get_goal_statistics(user_id: int) -> dict:
        """Get goals statistics for user."""
        goals = GoalsService.get_user_goals(user_id)
        
        total_goals = len(goals)
        completed_goals = len([g for g in goals if g.completed])
        active_goals = total_goals - completed_goals
        
        total_target = sum(g.target_amount for g in goals)
        total_saved = sum(g.current_amount for g in goals)
        
        overall_progress = (total_saved / total_target * 100) if total_target > 0 else 0
        
        return {
            'total_goals': total_goals,
            'completed_goals': completed_goals,
            'active_goals': active_goals,
            'total_target': Money(total_target, 'RUB'),
            'total_saved': Money(total_saved, 'RUB'),
            'overall_progress': overall_progress
        }


class SharedBudgetService:
    """Shared budget business logic service."""
    
    @staticmethod
    def generate_invitation_code() -> str:
        """Generate unique invitation code."""
        while True:
            code = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(8))
            
            # Check if code already exists
            existing = SharedBudget.query.filter_by(invitation_code=code).first()
            if not existing:
                return code
    
    @staticmethod
    def create_shared_budget(user_id: int, name: str, description: str = None) -> SharedBudget:
        """Create new shared budget."""
        budget = SharedBudget(
            name=name,
            description=description,
            owner_id=user_id,
            invitation_code=SharedBudgetService.generate_invitation_code()
        )
        db.session.add(budget)
        db.session.flush()  # Get the ID
        
        # Add creator as owner member
        member = SharedBudgetMember(
            budget_id=budget.id,
            user_id=user_id,
            role='owner'
        )
        db.session.add(member)
        db.session.commit()
        
        current_app.logger.info(f'Created shared budget {name} for user {user_id}')
        return budget
    
    @staticmethod
    def join_shared_budget(user_id: int, invitation_code: str) -> Optional[SharedBudget]:
        """Join shared budget by invitation code."""
        budget = SharedBudget.query.filter_by(invitation_code=invitation_code).first()
        if not budget:
            return None
        
        # Check if user is already a member
        existing_member = SharedBudgetMember.query.filter_by(
            budget_id=budget.id,
            user_id=user_id
        ).first()
        
        if existing_member:
            return budget  # Already a member
        
        # Add as member
        member = SharedBudgetMember(
            budget_id=budget.id,
            user_id=user_id,
            role='member'
        )
        db.session.add(member)
        db.session.commit()
        
        current_app.logger.info(f'User {user_id} joined shared budget {budget.id}')
        return budget
    
    @staticmethod
    def get_user_shared_budgets(user_id: int) -> List[SharedBudget]:
        """Get all shared budgets user is member of."""
        member_records = SharedBudgetMember.query.filter_by(user_id=user_id).all()
        budget_ids = [member.budget_id for member in member_records]
        
        if not budget_ids:
            return []
        
        return SharedBudget.query.filter(SharedBudget.id.in_(budget_ids)).all()
    
    @staticmethod
    def get_budget_members(budget_id: int) -> List[SharedBudgetMember]:
        """Get all members of shared budget."""
        return SharedBudgetMember.query.filter_by(budget_id=budget_id).all()
    
    @staticmethod
    def remove_member(budget_id: int, user_id: int, removed_by_user_id: int) -> bool:
        """Remove member from shared budget."""
        # Check if remover has permission (owner or removing themselves)
        remover_member = SharedBudgetMember.query.filter_by(
            budget_id=budget_id,
            user_id=removed_by_user_id
        ).first()
        
        if not remover_member:
            return False
        
        # Can only remove if you're the owner or removing yourself
        if remover_member.role != 'owner' and removed_by_user_id != user_id:
            return False
        
        # Find member to remove
        member_to_remove = SharedBudgetMember.query.filter_by(
            budget_id=budget_id,
            user_id=user_id
        ).first()
        
        if not member_to_remove:
            return False
        
        # Cannot remove the owner
        if member_to_remove.role == 'owner':
            return False
        
        db.session.delete(member_to_remove)
        db.session.commit()
        
        current_app.logger.info(f'Removed user {user_id} from shared budget {budget_id}')
        return True
    
    @staticmethod
    def update_member_role(budget_id: int, user_id: int, new_role: str, updated_by_user_id: int) -> bool:
        """Update member role in shared budget."""
        # Check if updater is owner
        updater_member = SharedBudgetMember.query.filter_by(
            budget_id=budget_id,
            user_id=updated_by_user_id
        ).first()
        
        if not updater_member or updater_member.role != 'owner':
            return False
        
        # Find member to update
        member = SharedBudgetMember.query.filter_by(
            budget_id=budget_id,
            user_id=user_id
        ).first()
        
        if not member:
            return False
        
        # Cannot change owner role
        if member.role == 'owner':
            return False
        
        # Valid roles
        valid_roles = ['member', 'viewer']
        if new_role not in valid_roles:
            return False
        
        member.role = new_role
        db.session.commit()
        
        current_app.logger.info(f'Updated user {user_id} role to {new_role} in shared budget {budget_id}')
        return True
    
    @staticmethod
    def delete_shared_budget(budget_id: int, user_id: int) -> bool:
        """Delete shared budget (owner only)."""
        budget = SharedBudget.query.filter_by(id=budget_id, owner_id=user_id).first()
        if not budget:
            return False
        
        db.session.delete(budget)
        db.session.commit()
        
        current_app.logger.info(f'Deleted shared budget {budget_id} by user {user_id}')
        return True
    
    @staticmethod
    def get_budget_summary(budget_id: int, user_id: int) -> Optional[dict]:
        """Get shared budget summary (if user is member)."""
        # Check if user is member
        member = SharedBudgetMember.query.filter_by(
            budget_id=budget_id,
            user_id=user_id
        ).first()
        
        if not member:
            return None
        
        budget = SharedBudget.query.get(budget_id)
        if not budget:
            return None
        
        members = SharedBudgetService.get_budget_members(budget_id)
        
        # TODO: Calculate budget statistics across all members
        # This would require integrating with budget service
        
        return {
            'budget': budget,
            'members': members,
            'user_role': member.role,
            'can_manage': member.role == 'owner'
        }