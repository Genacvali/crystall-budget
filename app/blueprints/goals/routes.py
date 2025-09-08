"""Goals routes."""
from flask import Blueprint
bp = Blueprint('goals', __name__)

@bp.route('/')
def list():
    return "Goals - Coming Soon"