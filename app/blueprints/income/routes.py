"""Income routes."""
from flask import Blueprint
bp = Blueprint('income', __name__)

@bp.route('/')
def list():
    return "Income - Coming Soon"