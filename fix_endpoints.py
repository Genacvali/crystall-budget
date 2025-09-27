#!/usr/bin/env python3
"""Script to fix endpoint names in templates to use blueprint format"""

from pathlib import Path
import re

# Mapping of old endpoint names to new blueprint-based names
ENDPOINT_MAPPING = {
    'login': 'auth.login',
    'logout': 'auth.logout', 
    'register': 'auth.register',
    'forgot_password': 'auth.forgot_password',
    'reset_password': 'auth.reset_password',
    'update_profile': 'auth.update_profile',
    'account_password': 'auth.account_password',
    
    'categories': 'budget.categories',
    'categories_add': 'budget.categories_add',
    'income': 'budget.income',
    'income_add': 'budget.income_add',
    'expenses': 'budget.expenses',
    'add_goal': 'budget.add_goal',
    'sources_add': 'budget.sources_add',
    'create_shared_budget': 'budget.create_shared_budget',
    'join_shared_budget': 'budget.join_shared_budget',
    'shared_budgets': 'budget.shared_budgets',
    'set_currency': 'budget.set_currency',
    'index': 'budget.index',
    'dashboard': 'budget.index',
    'account': 'budget.account',
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