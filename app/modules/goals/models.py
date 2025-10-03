"""Goals module models."""
from datetime import datetime
from decimal import Decimal
from app.core.extensions import db
from app.core.money import Money


class SavingsGoal(db.Model):
    """Savings goal model."""
    __tablename__ = 'savings_goals'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    target_amount = db.Column(db.Numeric(10, 2), nullable=False)
    current_amount = db.Column(db.Numeric(10, 2), default=0)
    currency = db.Column(db.String(3), default='RUB')
    target_date = db.Column(db.Date)
    completed = db.Column(db.Boolean, default=False)
    completed_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<SavingsGoal {self.title}>'
    
    @property
    def target_money(self):
        """Get target amount as Money object."""
        return Money(self.target_amount, self.currency)
    
    @property
    def current_money(self):
        """Get current amount as Money object."""
        return Money(self.current_amount, self.currency)
    
    @property
    def progress_percentage(self):
        """Calculate progress percentage."""
        if self.target_amount <= 0:
            return 0
        return min(100, (self.current_amount / self.target_amount) * 100)
    
    @property
    def remaining_money(self):
        """Get remaining amount as Money object."""
        remaining = max(Decimal('0'), self.target_amount - self.current_amount)
        return Money(remaining, self.currency)
    
    def add_progress(self, amount: Decimal) -> None:
        """Add progress to the goal."""
        self.current_amount += amount
        
        # Check if goal is completed
        if self.current_amount >= self.target_amount and not self.completed:
            self.completed = True
            self.completed_at = datetime.utcnow()
        
        db.session.commit()
    
    def to_dict(self):
        """Convert to dictionary."""
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'target_amount': float(self.target_amount),
            'current_amount': float(self.current_amount),
            'currency': self.currency,
            'target_date': self.target_date.isoformat() if self.target_date else None,
            'progress_percentage': float(self.progress_percentage),
            'completed': self.completed,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'created_at': self.created_at.isoformat()
        }


class SharedBudget(db.Model):
    """Shared family budget model."""
    __tablename__ = 'shared_budgets'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    creator_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    invite_code = db.Column(db.String(10), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Aliases for compatibility
    @property
    def owner_id(self):
        return self.creator_id

    @property
    def invitation_code(self):
        return self.invite_code
    
    # Relationships
    members = db.relationship('SharedBudgetMember', backref='budget', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<SharedBudget {self.name}>'
    
    def to_dict(self):
        """Convert to dictionary."""
        return {
            'id': self.id,
            'name': self.name,
            'owner_id': self.owner_id,
            'invitation_code': self.invitation_code,
            'created_at': self.created_at.isoformat(),
            'member_count': len(self.members)
        }


class SharedBudgetMember(db.Model):
    """Shared budget member model."""
    __tablename__ = 'shared_budget_members'
    
    id = db.Column(db.Integer, primary_key=True)
    budget_id = db.Column(db.Integer, db.ForeignKey('shared_budgets.id', ondelete='CASCADE'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    role = db.Column(db.String(20), default='member')  # 'owner', 'member', 'viewer'
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (db.UniqueConstraint('budget_id', 'user_id'),)
    
    def __repr__(self):
        return f'<SharedBudgetMember {self.user_id} in {self.budget_id}>'
    
    def to_dict(self):
        """Convert to dictionary."""
        return {
            'id': self.id,
            'budget_id': self.budget_id,
            'user_id': self.user_id,
            'role': self.role,
            'joined_at': self.joined_at.isoformat()
        }