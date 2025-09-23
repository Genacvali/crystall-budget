from flask import Blueprint

goals_bp = Blueprint('goals', __name__, url_prefix='/goals')

# Import routes to register them
from . import routes