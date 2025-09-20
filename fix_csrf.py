#!/usr/bin/env python3
"""Script to add CSRF tokens to all forms in templates"""

from pathlib import Path
import re

def add_csrf_to_template(template_path):
    """Add CSRF token to all forms in a template"""
    content = template_path.read_text(encoding='utf-8')
    
    # Check if form exists and csrf_token doesn't
    if '<form' in content and 'csrf_token' not in content:
        # Add csrf_token after each form opening tag
        content = re.sub(
            r'(<form[^>]*>)',
            r'\1\n    <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">',
            content,
            flags=re.IGNORECASE
        )
        
        template_path.write_text(content, encoding='utf-8')
        print(f"Added CSRF token to: {template_path}")
        return True
    return False

if __name__ == "__main__":
    templates_dir = Path("templates")
    fixed_count = 0
    
    for template_file in templates_dir.rglob("*.html"):
        if add_csrf_to_template(template_file):
            fixed_count += 1
    
    print(f"\nFixed {fixed_count} template files")