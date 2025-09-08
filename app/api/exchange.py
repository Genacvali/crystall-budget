"""Exchange rates API."""
from flask import Blueprint, request, jsonify
from ..services.currency import get_exchange_rate, convert_currency, CURRENCIES
from ..blueprints.auth.decorators import login_required
from ..db import get_db

bp = Blueprint('exchange', __name__)


@bp.route('/convert')
@login_required
def api_convert():
    """API для конвертации валют."""
    amount = request.args.get('amount', type=float)
    from_curr = request.args.get('from', '').upper()
    to_curr = request.args.get('to', '').upper()
    
    if not amount or not from_curr or not to_curr:
        return {"ok": False, "error": "Missing parameters"}, 400
    
    try:
        converted_amount = convert_currency(amount, from_curr, to_curr)
        rate = get_exchange_rate(from_curr, to_curr)
        
        return {
            "ok": True,
            "amount": amount,
            "from": from_curr,
            "to": to_curr,
            "converted": converted_amount,
            "rate": rate
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}, 500


@bp.route('/exchange-rates')
@login_required 
def get_exchange_rates():
    """API для получения курсов валют."""
    try:
        conn = get_db()
        
        # Проверяем кэш курсов (обновляем раз в час)
        cursor = conn.execute("""
        SELECT from_currency, to_currency, rate, updated_at 
        FROM exchange_rates 
        WHERE updated_at > datetime('now', '-1 hour')
        """)
        
        cached_rates = {}
        for row in cursor.fetchall():
            key = f"{row['from_currency']}_{row['to_currency']}"
            cached_rates[key] = float(row['rate'])
        
        # Если кэш пуст или нет нужных курсов, загружаем свежие данные
        currencies = ['RUB', 'USD', 'EUR', 'AMD', 'GEL']
        needed_pairs = []
        
        for from_curr in currencies:
            for to_curr in currencies:
                if from_curr != to_curr:
                    key = f"{from_curr}_{to_curr}"
                    if key not in cached_rates:
                        needed_pairs.append((from_curr, to_curr))
        
        # Загружаем недостающие курсы
        if needed_pairs:
            from flask import current_app
            for from_curr, to_curr in needed_pairs:
                try:
                    rate = get_exchange_rate(from_curr, to_curr)
                    if rate and rate > 0:
                        cached_rates[f"{from_curr}_{to_curr}"] = rate
                except Exception as e:
                    current_app.logger.warning(f"Failed to get rate {from_curr}->{to_curr}: {e}")
        
        conn.close()
        
        return {"ok": True, "rates": cached_rates}
        
    except Exception as e:
        from flask import current_app
        current_app.logger.error(f"Error in get_exchange_rates: {e}")
        return {"ok": False, "error": str(e)}, 500