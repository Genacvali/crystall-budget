"""Currency conversion service with exchange rate caching."""

import os
import requests
from datetime import datetime, timedelta
from flask import current_app, session

from ..db import get_db

# Configuration
CURRENCIES = {
    "RUB": {"symbol": "₽", "label": "Рубль"},
    "USD": {"symbol": "$", "label": "Доллар"},
    "EUR": {"symbol": "€", "label": "Евро"},
    "AMD": {"symbol": "֏", "label": "Драм"},
    "GEL": {"symbol": "₾", "label": "Лари"},
}
DEFAULT_CURRENCY = "RUB"
BRIDGE_CURRENCY = "USD"


def inject_currency():
    """Context processor for currency information."""
    code = session.get("currency", DEFAULT_CURRENCY)
    info = CURRENCIES.get(code, CURRENCIES[DEFAULT_CURRENCY])
    return dict(currency_code=code, currency_symbol=info["symbol"], currencies=CURRENCIES)


def _norm_cur(curr):
    """Нормализует валюту к верхнему регистру."""
    return str(curr).strip().upper()


def _fetch_rate_exchangerate_host(frm: str, to: str) -> float:
    """Прямой запрос к exchangerate.host"""
    url = "https://api.exchangerate.host/convert"
    r = requests.get(url, params={"from": frm, "to": to}, timeout=6)
    r.raise_for_status()
    data = r.json()
    if not data or "result" not in data or not data["result"]:
        raise ValueError("no result from exchangerate.host")
    return float(data["result"])


def _fetch_rate_exchangerate_host_base(base: str, sym: str) -> float:
    """Получить курс base -> sym одной пачкой"""
    url = "https://api.exchangerate.host/latest"
    r = requests.get(url, params={"base": base, "symbols": sym}, timeout=6)
    r.raise_for_status()
    data = r.json()
    rate = data.get("rates", {}).get(sym)
    if not rate:
        raise ValueError("no rate for symbol in latest")
    return float(rate)


def get_exchange_rate_via_bridge(frm: str, to: str, bridge: str = BRIDGE_CURRENCY) -> float:
    """Кросс-курс через промежуточную валюту (по умолчанию USD)."""
    frm, to, bridge = _norm_cur(frm), _norm_cur(to), _norm_cur(bridge)
    if frm == to:
        return 1.0
    if frm == bridge:
        # bridge -> to
        return _fetch_rate_exchangerate_host_base(bridge, to)
    if to == bridge:
        # frm -> bridge
        return _fetch_rate_exchangerate_host_base(frm, bridge)
    # frm -> bridge * bridge -> to
    r1 = _fetch_rate_exchangerate_host_base(frm, bridge)
    r2 = _fetch_rate_exchangerate_host_base(bridge, to)
    return float(r1) * float(r2)


def get_exchange_rate(frm: str, to: str) -> float:
    """
    1) читаем кэш из exchange_rates (TTL);
    2) пробуем прямую пару через exchangerate.host;
    3) пробуем кросс-курс через USD (или EXR_BRIDGE);
    4) сохраняем в кэш; если всё сломалось — отдаём старый кэш, если он был.
    """
    frm, to = _norm_cur(frm), _norm_cur(to)
    if frm == to:
        return 1.0

    now = datetime.utcnow()
    conn = get_db()
    try:
        conn.execute("PRAGMA foreign_keys=ON")
        row = conn.execute(
            "SELECT rate, updated_at FROM exchange_rates WHERE from_currency=? AND to_currency=?",
            (frm, to)
        ).fetchone()
        
        if row:
            try:
                updated = datetime.fromisoformat(row["updated_at"].replace("Z",""))
            except Exception:
                updated = now - timedelta(days=365)
            
            ttl_seconds = current_app.config.get('EXR_CACHE_TTL_SECONDS', 12 * 3600)
            if (now - updated).total_seconds() < ttl_seconds and row["rate"] and row["rate"] > 0:
                return float(row["rate"])

        # 2) прямая пара
        rate = None
        try:
            rate = _fetch_rate_exchangerate_host(frm, to)
        except Exception:
            # 3) кросс-курс
            try:
                rate = get_exchange_rate_via_bridge(frm, to, current_app.config.get('EXR_BRIDGE', 'USD'))
            except Exception:
                rate = None

        if rate and rate > 0:
            conn.execute(
                """
                INSERT INTO exchange_rates(from_currency, to_currency, rate, updated_at)
                VALUES(?,?,?,?)
                ON CONFLICT(from_currency, to_currency) DO UPDATE SET
                  rate=excluded.rate,
                  updated_at=excluded.updated_at
                """,
                (frm, to, float(rate), now.isoformat(timespec="seconds")+"Z"),
            )
            conn.commit()
            return float(rate)

        # 4) fallback: старый кэш, если был
        if row and row["rate"]:
            return float(row["rate"])

        raise RuntimeError(f"cannot fetch exchange rate {frm}->{to}")
        
    except Exception as e:
        current_app.logger.error(f"Exchange rate error {frm}->{to}: {e}")
        return 1.0  # Fallback
    finally:
        conn.close()


def convert_currency(amount, from_currency, to_currency):
    """Конвертирует сумму из одной валюты в другую."""
    if from_currency == to_currency:
        return amount
    
    try:
        rate = get_exchange_rate(from_currency, to_currency)
        return float(amount) * rate
    except Exception as e:
        current_app.logger.error(f"Currency conversion error: {e}")
        return amount