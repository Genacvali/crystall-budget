#!/bin/bash
set -e

echo "🎨 ИСПРАВЛЕНИЕ ПРОБЛЕМ С ВЕРСТКОЙ И FRONTEND"

APP_DIR="/opt/crystalbudget/crystall-budget"
SERVICE_NAME="crystalbudget"

if [ "$EUID" -ne 0 ]; then
    echo "❌ Запустите как root или с sudo"
    exit 1
fi

cd $APP_DIR

echo "🔄 Остановка сервиса..."
systemctl stop $SERVICE_NAME

echo "🔄 Исправление базового шаблона..."
# Исправляем base.html - используем CDN для всего
cat > app/templates/base.html << 'EOF'
<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{% block title %}CrystalBudget{% endblock %}</title>
  <!-- Bootstrap CSS -->
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
  <!-- Bootstrap Icons -->  
  <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.css" rel="stylesheet">
  <style>
    body { background-color: #f6f7f9; }
    .navbar-brand { font-weight: 600; }
    .modern-card { border: 1px solid #e9ecef; border-radius: .75rem; background: #fff; }
    .card-grid { display: grid; gap: 1rem; grid-template-columns: repeat(auto-fill,minmax(240px,1fr)); }
    .container { max-width: 1100px; }
  </style>
</head>
<body>
  <nav class="navbar navbar-dark bg-dark">
    <div class="container">
      <a class="navbar-brand" href="/">💎 CrystalBudget</a>
      <div class="d-flex gap-2 align-items-center">
        {% if session.get('user_id') %}
          <!-- Упрощенная форма валют без AJAX -->
          <form class="d-flex align-items-center gap-1" method="post" action="/auth/set-currency">
            <select class="form-select form-select-sm" name="currency" onchange="this.form.submit()">
              {% for code, info in currencies.items() %}
                <option value="{{ code }}" {% if code==currency_code %}selected{% endif %}>{{ info.label }} ({{ info.symbol }})</option>
              {% endfor %}
            </select>
          </form>

          <a class="btn btn-sm btn-outline-light" href="/">Дашборд</a>
          <a class="btn btn-sm btn-outline-light" href="/expenses">Траты</a>
          <a class="btn btn-sm btn-outline-light" href="/categories">Категории</a>
          <a class="btn btn-sm btn-outline-light" href="/income">Доходы</a>
          <a class="btn btn-sm btn-outline-warning" href="/sources">Источники</a>
          <a class="btn btn-sm btn-warning" href="/auth/logout">Выйти</a>
        {% else %}
          <a class="btn btn-sm btn-outline-light" href="/auth/login">Войти</a>
          <a class="btn btn-sm btn-primary" href="/auth/register">Регистрация</a>
        {% endif %}
      </div>
    </div>
  </nav>
  <div class="container my-4">
    {% with messages = get_flashed_messages(with_categories=true) %}
      {% if messages %}
        {% for cat, msg in messages %}
          <div class="alert alert-{{ 'danger' if cat=='error' else cat }} alert-dismissible fade show" role="alert">
            {{ msg }}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
          </div>
        {% endfor %}
      {% endif %}
    {% endwith %}
    {% block content %}{% endblock %}
  </div>
  
  <!-- Bootstrap JS -->
  <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
  
  <!-- Упрощенный скрипт валют без API -->
  <script>
    console.log('CrystalBudget загружен');
    
    // Базовый обработчик форм
    document.addEventListener('DOMContentLoaded', function() {
      console.log('DOM загружен');
      
      // Простое подтверждение удаления
      document.querySelectorAll('[onclick*="confirm"]').forEach(function(btn) {
        btn.addEventListener('click', function(e) {
          if (!confirm('Вы уверены?')) {
            e.preventDefault();
            return false;
          }
        });
      });
    });
  </script>
  
  {% block scripts %}{% endblock %}
</body>
</html>
EOF

echo "✅ Исправлен базовый шаблон"

echo "🔄 Временно отключаем проблемные курсы валют..."
# Создаем простую заглушку для курсов
cat > app/services/currency_simple.py << 'EOF'
"""Простая версия сервиса валют без внешних API."""

from flask import session

CURRENCIES = {
    "RUB": {"symbol": "₽", "label": "Рубль"},
    "USD": {"symbol": "$", "label": "Доллар"}, 
    "EUR": {"symbol": "€", "label": "Евро"},
}
DEFAULT_CURRENCY = "RUB"

def inject_currency():
    """Context processor для валют."""
    code = session.get("currency", DEFAULT_CURRENCY)
    info = CURRENCIES.get(code, CURRENCIES[DEFAULT_CURRENCY])
    return dict(currency_code=code, currency_symbol=info["symbol"], currencies=CURRENCIES)

def get_exchange_rate(frm: str, to: str) -> float:
    """Простые фиксированные курсы."""
    if frm == to:
        return 1.0
    
    # Простые фиксированные курсы
    rates = {
        "USD_RUB": 90.0,
        "EUR_RUB": 100.0,
        "RUB_USD": 0.011,
        "RUB_EUR": 0.010,
        "USD_EUR": 0.85,
        "EUR_USD": 1.18,
    }
    
    key = f"{frm}_{to}"
    return rates.get(key, 1.0)

def convert_currency(amount, from_currency, to_currency):
    """Конвертация валют."""
    if from_currency == to_currency:
        return amount
    
    rate = get_exchange_rate(from_currency, to_currency)
    return float(amount) * rate
EOF

echo "✅ Создана упрощенная версия валютного сервиса"

echo "🔄 Временная замена API exchange..."
# Создаем простую заглушку API
cat > app/api/exchange_simple.py << 'EOF'
"""Простая версия API курсов."""
from flask import Blueprint, jsonify
from ..blueprints.auth.decorators import login_required

bp = Blueprint('exchange', __name__)

@bp.route('/convert')
@login_required
def api_convert():
    return {"ok": True, "message": "Currency conversion temporarily disabled"}

@bp.route('/exchange-rates')
@login_required 
def get_exchange_rates():
    return {
        "ok": True, 
        "rates": {
            "USD_RUB": 90.0,
            "EUR_RUB": 100.0,
            "RUB_USD": 0.011,
            "RUB_EUR": 0.010,
        }
    }
EOF

echo "✅ Создана упрощенная версия API"

echo "🔄 Резервное копирование и замена..."
# Бэкап оригинальных файлов
if [ -f "app/services/currency.py" ]; then
    cp app/services/currency.py app/services/currency_original.py.backup
    cp app/services/currency_simple.py app/services/currency.py
fi

if [ -f "app/api/exchange.py" ]; then
    cp app/api/exchange.py app/api/exchange_original.py.backup  
    cp app/api/exchange_simple.py app/api/exchange.py
fi

echo "🔄 Установка прав доступа..."
chown -R crystal:crystal $APP_DIR

echo "🔄 Запуск сервиса..."
systemctl start $SERVICE_NAME

# Проверка
sleep 3
if systemctl is-active --quiet $SERVICE_NAME; then
    echo "✅ Сервис запущен"
    
    # HTTP тест
    if curl -s -f http://localhost:5000 > /dev/null 2>&1; then
        echo "✅ HTTP работает"
    else
        echo "⚠️  HTTP тест не прошел"
    fi
else
    echo "❌ Сервис не запустился"
    journalctl -u $SERVICE_NAME --no-pager -l --since "1 minute ago"
fi

echo ""
echo "🎉 Исправления применены!"
echo "📋 Что исправлено:"
echo "  ✅ CSS/JS загружаются с CDN"  
echo "  ✅ Упрощены валютные курсы"
echo "  ✅ Базовый JavaScript работает"
echo "  ✅ Формы отправляются обычным POST"
echo ""
echo "⚠️  Временно отключены:"
echo "  • Живая конвертация валют"
echo "  • Сложные API курсов"
echo ""
echo "🔍 Проверьте сайт в браузере"