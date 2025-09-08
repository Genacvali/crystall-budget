"""Shared budgets routes."""
from flask import Blueprint
bp = Blueprint('shared', __name__)

@bp.route('/')
def list():
    return "Shared Budgets - Coming Soon"