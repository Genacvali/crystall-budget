"""Issue tracker models."""
from datetime import datetime
from enum import Enum
from app.core.extensions import db


class IssuePriority(Enum):
    """Issue priority levels."""
    BLOCKER = "blocker"     # Critical issues blocking functionality  
    MAJOR = "major"         # Important issues with data/logic problems
    MINOR = "minor"         # UI/UX issues, cosmetic problems


class IssueStatus(Enum):
    """Issue status states."""
    BACKLOG = "backlog"     # New issues waiting to be triaged
    TODO = "todo"           # Ready to be worked on
    IN_PROGRESS = "in_progress"  # Currently being worked on
    TESTING = "testing"     # Under review/testing
    DONE = "done"           # Completed and deployed


class Issue(db.Model):
    """Issue tracking model."""
    __tablename__ = 'issues'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Basic info
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    
    # Classification
    priority = db.Column(db.Enum(IssuePriority), nullable=False, default=IssuePriority.MINOR)
    status = db.Column(db.Enum(IssueStatus), nullable=False, default=IssueStatus.BACKLOG)
    
    # Assignment
    assignee = db.Column(db.String(100), nullable=True)  # Who is working on it
    reporter = db.Column(db.String(100), nullable=False)  # Who reported it
    
    # Technical details
    endpoint = db.Column(db.String(200), nullable=True)  # Related endpoint
    error_message = db.Column(db.Text, nullable=True)    # Error details
    user_agent = db.Column(db.String(500), nullable=True) # Browser/client info
    reproduction_steps = db.Column(db.Text, nullable=True)
    
    # Acceptance criteria
    acceptance_criteria = db.Column(db.Text, nullable=True)
    
    # Screenshots/attachments
    screenshot_before = db.Column(db.String(255), nullable=True)
    screenshot_after = db.Column(db.String(255), nullable=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    resolved_at = db.Column(db.DateTime, nullable=True)
    
    # Metrics
    estimated_hours = db.Column(db.Float, nullable=True)
    actual_hours = db.Column(db.Float, nullable=True)
    
    def __repr__(self):
        return f'<Issue {self.id}: {self.title}>'
    
    @property
    def priority_color(self):
        """Get color for priority display."""
        colors = {
            IssuePriority.BLOCKER: 'danger',
            IssuePriority.MAJOR: 'warning', 
            IssuePriority.MINOR: 'info'
        }
        return colors.get(self.priority, 'secondary')
    
    @property
    def status_color(self):
        """Get color for status display."""
        colors = {
            IssueStatus.BACKLOG: 'secondary',
            IssueStatus.TODO: 'primary',
            IssueStatus.IN_PROGRESS: 'warning',
            IssueStatus.TESTING: 'info',
            IssueStatus.DONE: 'success'
        }
        return colors.get(self.status, 'secondary')
    
    @property
    def is_blocking(self):
        """Check if this is a blocking issue."""
        return self.priority == IssuePriority.BLOCKER
    
    @property
    def days_open(self):
        """Get number of days since issue was opened."""
        if self.resolved_at:
            return (self.resolved_at - self.created_at).days
        return (datetime.utcnow() - self.created_at).days
    
    def to_dict(self):
        """Convert to dictionary for JSON responses."""
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'priority': self.priority.value if self.priority else None,
            'priority_color': self.priority_color,
            'status': self.status.value if self.status else None,
            'status_color': self.status_color,
            'assignee': self.assignee,
            'reporter': self.reporter,
            'endpoint': self.endpoint,
            'error_message': self.error_message,
            'reproduction_steps': self.reproduction_steps,
            'acceptance_criteria': self.acceptance_criteria,
            'screenshot_before': self.screenshot_before,
            'screenshot_after': self.screenshot_after,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None,
            'estimated_hours': self.estimated_hours,
            'actual_hours': self.actual_hours,
            'days_open': self.days_open,
            'is_blocking': self.is_blocking
        }
    
    @classmethod
    def create_from_error(cls, error_details: dict, reporter: str = 'system'):
        """Create issue from error details."""
        title = f"Error {error_details.get('status_code', 500)} on {error_details.get('endpoint', 'unknown')}"
        
        # Determine priority based on status code
        status_code = error_details.get('status_code', 500)
        if status_code >= 500:
            priority = IssuePriority.BLOCKER
        elif status_code == 404:
            priority = IssuePriority.MINOR
        else:
            priority = IssuePriority.MAJOR
        
        description_parts = []
        if error_details.get('exception'):
            description_parts.append(f"**Error:** {error_details['exception']}")
        if error_details.get('url'):
            description_parts.append(f"**URL:** {error_details['url']}")
        if error_details.get('method'):
            description_parts.append(f"**Method:** {error_details['method']}")
        
        return cls(
            title=title,
            description='\n\n'.join(description_parts),
            priority=priority,
            reporter=reporter,
            endpoint=error_details.get('endpoint'),
            error_message=error_details.get('exception'),
            user_agent=error_details.get('user_agent')
        )


class IssueComment(db.Model):
    """Comments on issues."""
    __tablename__ = 'issue_comments'
    
    id = db.Column(db.Integer, primary_key=True)
    issue_id = db.Column(db.Integer, db.ForeignKey('issues.id'), nullable=False)
    
    author = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    issue = db.relationship('Issue', backref=db.backref('comments', lazy='dynamic', order_by='IssueComment.created_at'))
    
    def __repr__(self):
        return f'<IssueComment {self.id} for Issue {self.issue_id}>'