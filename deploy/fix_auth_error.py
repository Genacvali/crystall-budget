#!/usr/bin/env python3
"""
Скрипт для исправления ошибки аутентификации в production.
Исправляет использование sqlite3.Row.get() -> sqlite3.Row[]
"""

import os

AUTH_ROUTES_FILE = "/opt/crystalbudget/crystall-budget/app/blueprints/auth/routes.py"

def fix_auth_routes():
    """Исправить auth routes для работы с sqlite3.Row"""
    
    if not os.path.exists(AUTH_ROUTES_FILE):
        print(f"❌ Файл не найден: {AUTH_ROUTES_FILE}")
        return False
    
    # Читаем файл
    with open(AUTH_ROUTES_FILE, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Создаем резервную копию
    backup_file = AUTH_ROUTES_FILE + ".backup"
    with open(backup_file, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"✅ Создана резервная копия: {backup_file}")
    
    # Исправления
    fixes = [
        # В функции login
        ("session['theme'] = user.get('theme', 'light')", 
         "session['theme'] = user['theme'] if 'theme' in user.keys() else 'light'"),
        
        ("session['currency'] = user.get('default_currency', 'RUB')",
         "session['currency'] = user['default_currency'] if 'default_currency' in user.keys() else 'RUB'"),
    ]
    
    # Применяем исправления
    for old, new in fixes:
        if old in content:
            content = content.replace(old, new)
            print(f"✅ Исправлено: {old[:50]}...")
    
    # Записываем исправленный файл
    with open(AUTH_ROUTES_FILE, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ Файл auth/routes.py исправлен")
    return True

if __name__ == "__main__":
    print("🔧 Исправление ошибки sqlite3.Row.get()")
    if fix_auth_routes():
        print("🎉 Исправления применены! Перезапустите сервис:")
        print("   sudo systemctl restart crystalbudget")
    else:
        print("❌ Не удалось применить исправления")