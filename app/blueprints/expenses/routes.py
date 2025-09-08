"""Expenses routes."""
from flask import Blueprint
bp = Blueprint('expenses', __name__)

@bp.route('/')
def list_add():
    return "Expenses - Coming Soon"