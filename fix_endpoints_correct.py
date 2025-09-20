#!/usr/bin/env python3
"""Script to fix endpoint names back to monolithic format"""

from pathlib import Path
import re

# Correct mapping for monolithic app (no blueprints)
ENDPOINT_MAPPING = {
    # Auth endpoints
    'auth.login': 'login',
    'auth.logout': 'logout', 
    'auth.register': 'register',
    'auth.forgot_password': 'forgot_password',
    'auth.reset_password': 'reset_password',
    'auth.update_profile': 'update_profile',
    'auth.account_password': 'account_password',
    
    # Budget endpoints - these likely don't exist as budget.* in monolith
    'budget.categories': 'categories',
    'budget.categories_add': 'categories_add',
    'budget.income': 'income',
    'budget.income_add': 'income_add', 
    'budget.expenses': 'expenses',
    'budget.add_goal': 'add_goal',
    'budget.sources_add': 'sources_add',
    'budget.create_shared_budget': 'create_shared_budget',
    'budget.join_shared_budget': 'join_shared_budget',
    'budget.shared_budgets': 'shared_budgets',
    'budget.set_currency': 'set_currency',
    'budget.account': 'account',
}

def fix_endpoints_in_template(template_path):
    """Fix endpoint names in a template"""
    content = template_path.read_text(encoding='utf-8')
    original_content = content
    
    for old_endpoint, new_endpoint in ENDPOINT_MAPPING.items():
        # Pattern to match url_for('old_endpoint')
        pattern = rf"url_for\(['\"]({re.escape(old_endpoint)})['\"]\)"
        replacement = f"url_for('{new_endpoint}')"
        content = re.sub(pattern, replacement, content)
    
    if content != original_content:
        template_path.write_text(content, encoding='utf-8')
        print(f"Fixed endpoints in: {template_path}")
        return True
    return False

if __name__ == "__main__":
    templates_dir = Path("templates")
    fixed_count = 0
    
    for template_file in templates_dir.rglob("*.html"):
        if fix_endpoints_in_template(template_file):
            fixed_count += 1
    
    print(f"\nFixed {fixed_count} template files")