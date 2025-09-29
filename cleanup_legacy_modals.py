#!/usr/bin/env python3
"""Automated legacy modal cleanup script."""
import re
import os
from pathlib import Path

def clean_template_file(file_path):
    """Clean legacy modal code from a template file."""
    print(f"🧹 Cleaning {file_path}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    
    # 1. Replace data-bs-toggle="modal" with data-modal-url
    # For goals
    content = re.sub(
        r'data-bs-toggle="modal"\s+data-bs-target="#addGoalModal"',
        r'data-modal-url="{{ url_for(\'modals.goal_add\') }}"',
        content
    )
    
    # For categories  
    content = re.sub(
        r'data-bs-toggle="modal"\s+data-bs-target="#addCategoryModal"',
        r'data-modal-url="{{ url_for(\'modals.category_add\') }}"',
        content
    )
    
    # For shared budgets
    content = re.sub(
        r'data-bs-toggle="modal"\s+data-bs-target="#createBudgetModal"',
        r'data-modal-url="{{ url_for(\'modals.shared_budget_create\') }}"',
        content
    )
    
    # Generic modal triggers - need to identify manually
    
    # 2. Remove large legacy modal HTML blocks (be very careful)
    # Remove addGoalModal
    modal_pattern = r'<!-- Модалка: Новая цель -->.*?</div>\s*<!-- /modal -->'
    content = re.sub(modal_pattern, '', content, flags=re.DOTALL)
    
    # Remove addCategoryModal (if found)
    modal_pattern = r'<!-- Модальное окно добавления категории -->.*?</div>\s*<!-- /modal -->'
    content = re.sub(modal_pattern, '', content, flags=re.DOTALL)
    
    # 3. Remove legacy modal divs by ID
    patterns_to_remove = [
        r'<div class="modal fade" id="addGoalModal".*?</div>\s*</div>\s*</div>',
        r'<div class="modal fade" id="addCategoryModal".*?</div>\s*</div>\s*</div>',
        r'<div class="modal fade" id="createBudgetModal".*?</div>\s*</div>\s*</div>',
    ]
    
    for pattern in patterns_to_remove:
        content = re.sub(pattern, '', content, flags=re.DOTALL)
    
    # 4. Clean up empty lines (max 2 consecutive)
    content = re.sub(r'\n{3,}', '\n\n', content)
    
    # Only write if content changed
    if content != original_content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"  ✅ Updated {file_path}")
        return True
    else:
        print(f"  ℹ️  No changes needed for {file_path}")
        return False

def main():
    """Main cleanup function."""
    print("🚀 LEGACY MODAL CLEANUP SCRIPT")
    print("=" * 50)
    
    # Files to clean
    template_files = [
        "/opt/crystall-budget/templates/goals/goals.html",
        "/opt/crystall-budget/templates/budget/categories.html", 
        "/opt/crystall-budget/templates/categories.html",
        "/opt/crystall-budget/templates/shared_budgets.html",
        "/opt/crystall-budget/templates/shared_budget_detail.html",
        "/opt/crystall-budget/templates/goals/shared_budgets.html",
        "/opt/crystall-budget/templates/goals/shared_budget_detail.html",
        "/opt/crystall-budget/templates/components/_balance_panel.html"
    ]
    
    updated_files = 0
    
    for file_path in template_files:
        if os.path.exists(file_path):
            if clean_template_file(file_path):
                updated_files += 1
        else:
            print(f"⚠️  File not found: {file_path}")
    
    print(f"\n✅ Cleanup completed! Updated {updated_files} files.")
    print("🎯 Next: Test the application to ensure everything works correctly.")

if __name__ == "__main__":
    main()