"""Family sharing service."""
import secrets
from typing import Optional, List
from app.core.extensions import db
from app.modules.goals.models import SharedBudget
from .models import User


class FamilyService:
    """Service for managing family budget access."""

    @staticmethod
    def create_family_access(user_id: int, name: str = None) -> SharedBudget:
        """Create family access for user.

        Args:
            user_id: User ID creating the family
            name: Optional name for the family budget

        Returns:
            Created SharedBudget instance
        """
        user = User.query.get(user_id)
        if not user:
            raise ValueError("User not found")

        if user.has_family_access:
            raise ValueError("User already has family access")

        # Generate unique invitation code
        invitation_code = FamilyService._generate_invitation_code()

        # Create shared budget
        budget_name = name or f"Семейный бюджет {user.display_name}"
        shared_budget = SharedBudget(
            name=budget_name,
            creator_id=user_id,
            invite_code=invitation_code
        )
        db.session.add(shared_budget)
        db.session.flush()  # Get ID

        # Link user to shared budget
        user.shared_budget_id = shared_budget.id
        db.session.commit()

        return shared_budget

    @staticmethod
    def join_family(user_id: int, invitation_code: str) -> Optional[SharedBudget]:
        """Join family budget by invitation code.

        Args:
            user_id: User ID joining the family
            invitation_code: Invitation code

        Returns:
            SharedBudget if successful, None if code is invalid
        """
        user = User.query.get(user_id)
        if not user:
            raise ValueError("User not found")

        if user.has_family_access:
            raise ValueError("User already has family access")

        # Find shared budget by invitation code
        shared_budget = SharedBudget.query.filter_by(invite_code=invitation_code).first()
        if not shared_budget:
            return None

        # Link user to shared budget
        user.shared_budget_id = shared_budget.id
        db.session.commit()

        return shared_budget

    @staticmethod
    def leave_family(user_id: int) -> bool:
        """Leave family budget.

        Args:
            user_id: User ID leaving the family

        Returns:
            True if successful, False if user wasn't in a family
        """
        user = User.query.get(user_id)
        if not user or not user.has_family_access:
            return False

        shared_budget_id = user.shared_budget_id

        # Remove user from family
        user.shared_budget_id = None
        db.session.commit()

        # Check if family is now empty
        remaining_members = User.query.filter_by(shared_budget_id=shared_budget_id).count()
        if remaining_members == 0:
            # Delete empty shared budget
            shared_budget = SharedBudget.query.get(shared_budget_id)
            if shared_budget:
                db.session.delete(shared_budget)
                db.session.commit()

        return True

    @staticmethod
    def get_family_info(user_id: int) -> Optional[dict]:
        """Get family information for user.

        Args:
            user_id: User ID

        Returns:
            Dictionary with family info or None if not in family
        """
        user = User.query.get(user_id)
        if not user or not user.has_family_access:
            return None

        shared_budget = SharedBudget.query.get(user.shared_budget_id)
        if not shared_budget:
            return None

        family_members = user.get_family_members()

        return {
            'budget': shared_budget,
            'invitation_code': shared_budget.invitation_code,
            'is_owner': shared_budget.owner_id == user_id,
            'members': family_members,
            'member_count': len(family_members)
        }

    @staticmethod
    def get_invitation_code(user_id: int) -> Optional[str]:
        """Get invitation code for user's family.

        Args:
            user_id: User ID

        Returns:
            Invitation code or None if user not in family
        """
        user = User.query.get(user_id)
        if not user or not user.has_family_access:
            return None

        shared_budget = SharedBudget.query.get(user.shared_budget_id)
        if not shared_budget:
            return None

        return shared_budget.invitation_code

    @staticmethod
    def regenerate_invitation_code(user_id: int) -> Optional[str]:
        """Regenerate invitation code (owner only).

        Args:
            user_id: User ID (must be owner)

        Returns:
            New invitation code or None if not authorized
        """
        user = User.query.get(user_id)
        if not user or not user.has_family_access:
            return None

        shared_budget = SharedBudget.query.get(user.shared_budget_id)
        if not shared_budget or shared_budget.owner_id != user_id:
            return None

        # Generate new code
        new_code = FamilyService._generate_invitation_code()
        shared_budget.invite_code = new_code
        db.session.commit()

        return new_code

    @staticmethod
    def _generate_invitation_code(length: int = 8) -> str:
        """Generate unique invitation code.

        Args:
            length: Code length

        Returns:
            Random alphanumeric code
        """
        while True:
            code = secrets.token_urlsafe(length)[:length].upper()
            # Check uniqueness
            existing = SharedBudget.query.filter_by(invite_code=code).first()
            if not existing:
                return code
