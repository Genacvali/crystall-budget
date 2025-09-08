"""WSGI entry point for Crystal Budget application."""

import os
from app import create_app

# Create application instance
app = create_app()

if __name__ == "__main__":
    # For development only
    if app.config['SECRET_KEY'] == 'dev-only-insecure-key-change-in-production':
        print("WARNING: Using insecure default secret key. Set SECRET_KEY environment variable for production!")
    
    app.run(
        host="0.0.0.0", 
        port=int(os.environ.get("PORT", 5000)), 
        debug=os.environ.get("FLASK_ENV") == "development"
    )