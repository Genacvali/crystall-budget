"""
Интеграция Telegram с Flask приложением
Добавить эти функции в app.py
"""

# Добавить в app.py после других импортов:
# from datetime import datetime, timedelta
# import secrets
# import string

# Добавить эти функции в app.py:

@app.route("/reset-password", methods=["GET", "POST"])
def reset_password_telegram():
    """Сброс пароля через Telegram токен"""
    token = request.args.get("token") or request.form.get("token")
    
    if request.method == "GET":
        if not token:
            flash("Неверная ссылка сброса пароля", "error")
            return redirect(url_for("login"))
        
        # Проверяем токен
        conn = get_db()
        cursor = conn.execute("""
            SELECT prt.user_id, u.email, u.name
            FROM password_reset_tokens prt
            JOIN users u ON prt.user_id = u.id
            WHERE prt.token = ? AND prt.expires_at > ? AND prt.used = 0
        """, (token, datetime.now().isoformat()))
        
        user = cursor.fetchone()
        conn.close()
        
        if not user:
            flash("Ссылка сброса пароля недействительна или истекла", "error")
            return redirect(url_for("login"))
        
        return render_template("reset_password.html", 
                             token=token, 
                             user_email=user["email"],
                             user_name=user["name"])
    
    # POST - обработка сброса пароля
    new_password = request.form.get("new_password")
    confirm_password = request.form.get("confirm_password")
    
    if not new_password or not confirm_password:
        flash("Заполните все поля", "error")
        return redirect(url_for("reset_password_telegram", token=token))
    
    if new_password != confirm_password:
        flash("Пароли не совпадают", "error")
        return redirect(url_for("reset_password_telegram", token=token))
    
    if len(new_password) < 6:
        flash("Пароль должен содержать минимум 6 символов", "error")
        return redirect(url_for("reset_password_telegram", token=token))
    
    # Сбрасываем пароль
    conn = get_db()
    try:
        # Проверяем токен еще раз
        cursor = conn.execute("""
            SELECT user_id FROM password_reset_tokens 
            WHERE token = ? AND expires_at > ? AND used = 0
        """, (token, datetime.now().isoformat()))
        
        user_row = cursor.fetchone()
        if not user_row:
            flash("Ссылка сброса пароля недействительна", "error")
            return redirect(url_for("login"))
        
        user_id = user_row["user_id"]
        
        # Обновляем пароль
        from werkzeug.security import generate_password_hash
        password_hash = generate_password_hash(new_password)
        
        conn.execute(
            "UPDATE users SET password_hash = ? WHERE id = ?",
            (password_hash, user_id)
        )
        
        # Помечаем токен как использованный
        conn.execute(
            "UPDATE password_reset_tokens SET used = 1 WHERE token = ?",
            (token,)
        )
        
        conn.commit()
        
        flash("Пароль успешно изменен! Войдите с новым паролем", "success")
        app.logger.info(f"Password reset successfully for user {user_id} via Telegram")
        return redirect(url_for("login"))
        
    except Exception as e:
        app.logger.error(f"Error resetting password: {e}")
        flash("Ошибка при сбросе пароля", "error")
        return redirect(url_for("login"))
    finally:
        conn.close()

@app.route("/profile/telegram", methods=["GET", "POST"])
@login_required
def profile_telegram():
    """Управление Telegram интеграцией в профиле"""
    uid = session["user_id"]
    conn = get_db()
    
    if request.method == "GET":
        # Получаем информацию о связанном Telegram
        cursor = conn.execute("""
            SELECT telegram_id, telegram_username, telegram_first_name, 
                   telegram_last_name, is_verified, verified_at
            FROM user_telegram 
            WHERE user_id = ?
        """, (uid,))
        
        telegram_info = cursor.fetchone()
        conn.close()
        
        return render_template("profile_telegram.html", telegram_info=telegram_info)
    
    # POST - отвязать Telegram
    if request.form.get("action") == "unlink":
        conn.execute("DELETE FROM user_telegram WHERE user_id = ?", (uid,))
        conn.commit()
        conn.close()
        
        flash("Telegram успешно отвязан", "success")
        app.logger.info(f"Telegram unlinked for user {uid}")
        return redirect(url_for("profile_telegram"))

def create_telegram_reset_token(user_id):
    """Создать токен для сброса пароля через Telegram"""
    token = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(32))
    expires_at = datetime.now() + timedelta(hours=1)
    
    conn = get_db()
    try:
        conn.execute("""
            INSERT INTO password_reset_tokens 
            (user_id, token, expires_at)
            VALUES (?, ?, ?)
        """, (user_id, token, expires_at.isoformat()))
        conn.commit()
        return token
    finally:
        conn.close()

def send_telegram_notification(user_id, message):
    """Отправить уведомление в Telegram (если настроен)"""
    # Эту функцию можно использовать для отправки уведомлений
    # о превышении бюджета, достижении целей и т.д.
    pass