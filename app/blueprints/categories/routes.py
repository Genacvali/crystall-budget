"""Categories routes."""
from flask import Blueprint
bp = Blueprint('categories', __name__)

@bp.route('/')
def list():
    return "Categories - Coming Soon"