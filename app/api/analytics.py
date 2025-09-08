"""Analytics API."""
from flask import Blueprint

bp = Blueprint('analytics', __name__)

@bp.route('/expenses/chart-data')
def chart_data():
    return {"ok": True, "data": [], "message": "Coming soon"}

@bp.route('/expenses/compare') 
def compare():
    return {"ok": True, "data": [], "message": "Coming soon"}