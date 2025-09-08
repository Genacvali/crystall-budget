"""Sources routes."""
from flask import Blueprint
bp = Blueprint('sources', __name__)

@bp.route('/')
def list():
    return "Sources - Coming Soon"