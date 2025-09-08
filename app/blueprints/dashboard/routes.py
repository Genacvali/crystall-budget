"""Dashboard routes."""

from flask import Blueprint, render_template, session

from ..auth.decorators import login_required

bp = Blueprint('dashboard', __name__)


@bp.route('/')
@login_required
def index():
    """Main dashboard page."""
    return render_template('dashboard.html', user_name=session.get('name', 'User'))