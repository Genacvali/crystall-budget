from flask import Blueprint

budget_bp = Blueprint('budget', __name__)

# Import routes to register them  
from . import routes