#!/usr/bin/env bash
# CrystalBudget — единый тест-раннер локально и в CI.
# Требования к приложению:
#  - конфиг TestingConfig: TESTING=True, WTF_CSRF_ENABLED=False, LOGIN_DISABLED=True
#  - create_app() читает APP_CONFIG=testing (или принимает имя конфига и выбирает его)
#  - эндпоинт /healthz (200 OK)
# Запуск: APP_PORT=5000 ./scripts/ci-check.sh [--suite api|e2e|smoke|all] [--no-e2e] [--fast]

set -euo pipefail

# ---------- Настройки ----------
APP_HOST="${APP_HOST:-127.0.0.1}"
APP_PORT="${APP_PORT:-5001}"
BASE_URL="http://${APP_HOST}:${APP_PORT}"

TEST_DB_PATH="${TEST_DB_PATH:-./test_local.db}"
TEST_DB_URI="sqlite:///${TEST_DB_PATH}"
SECRET_KEY="${SECRET_KEY:-test-secret-key-local}"

# критично: должен включать TESTING=True, WTF_CSRF_ENABLED=False
APP_CONFIG="${APP_CONFIG:-testing}"

SUITE="all"
RUN_E2E=true
FAST=false

# ---------- Аргументы ----------
while [[ $# -gt 0 ]]; do
  case "$1" in
    --suite) SUITE="$2"; shift 2;;
    --no-e2e) RUN_E2E=false; shift;;
    --fast) FAST=true; shift;;
    --port) APP_PORT="$2"; BASE_URL="http://${APP_HOST}:${APP_PORT}"; shift 2;;
    *) echo "Unknown arg: $1"; exit 2;;
  esac
done

# ---------- Цвета ----------
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
say(){ echo -e "$1"; }; ok(){ say "${GREEN}$1${NC}"; }; warn(){ say "${YELLOW}$1${NC}"; }; bad(){ say "${RED}$1${NC}"; }

say "${YELLOW}🧪 CrystalBudget — тест-раннер${NC}"
echo "BASE_URL=${BASE_URL}"
echo "DB=${TEST_DB_URI}"
echo "APP_CONFIG=${APP_CONFIG}"
echo "SUITE=${SUITE}  FAST=${FAST}  E2E=${RUN_E2E}"

# ---------- .venv ----------
if [[ -z "${VIRTUAL_ENV:-}" ]]; then
  warn "⚠️  Активирую .venv …"
  source .venv/bin/activate || { bad "Нет .venv — создайте и установите зависимости"; exit 1; }
fi

# ---------- Тестовые зависимости ----------
python - <<'PY' >/dev/null 2>&1 || pip install -q -r requirements-test.txt
import importlib, sys
for mod in ("pytest","pytest_html","pytest_metadata","playwright"):
    try: importlib.import_module(mod)
    except Exception: sys.exit(1)
PY

# необязательная установка браузера для e2e
python - <<'PY' >/dev/null 2>&1 || true
try:
    import playwright.__main__ as p; p.main(["install","--with-deps","chromium"])
except Exception:
    pass
PY

# ---------- Подготовка БД ----------
warn "🗄️  Готовлю тестовую БД …"
export BUDGET_DB="${TEST_DB_URI}"
export SECRET_KEY="${SECRET_KEY}"
export APP_CONFIG="${APP_CONFIG}"
export TESTING=1
rm -f "${TEST_DB_PATH}"

python - <<'PY'
import os
from app import create_app
from app.core.extensions import db
cfg = os.getenv("APP_CONFIG","testing")
try:
    app = create_app(cfg)  # если create_app принимает имя конфига
except TypeError:
    app = create_app()     # иначе внутри фабрика обязана читать APP_CONFIG сама
with app.app_context():
    db.create_all()
    print("✅ Test DB ready; TESTING=", app.config.get("TESTING"), "CSRF=", app.config.get("WTF_CSRF_ENABLED"))
PY

# ---------- Хелперы ----------
PID_FILE=".tmp_test_server.pid"
mkdir -p .tmp .pytest_cache || true

wait_http_ok () {
  local url="$1" max_tries="${2:-80}" delay="${3:-0.25}"
  for ((i=1;i<=max_tries;i++)); do
    if curl -sSf -m 2 "$url" >/dev/null; then return 0; fi
    sleep "$delay"
  done
  return 1
}

kill_if_running () {
  if [[ -f "$PID_FILE" ]]; then
    local pid; pid=$(cat "$PID_FILE" || true)
    if [[ -n "${pid:-}" ]] && ps -p "$pid" >/dev/null 2>&1; then
      kill "$pid" 2>/dev/null || true
      sleep 0.5
      pkill -P "$pid" 2>/dev/null || true
      kill -9 "$pid" 2>/dev/null || true
    fi
    rm -f "$PID_FILE"
  fi
}

start_server () {
  warn "🚀 Стартую тестовый сервер на ${BASE_URL} …"
  nohup python - <<PY >/dev/null 2>&1 &
import os
from app import create_app
cfg = os.getenv("APP_CONFIG","testing")
try:
    app = create_app(cfg)
except TypeError:
    app = create_app()
app.logger.setLevel("WARNING")
app.run(host=os.getenv("APP_HOST","127.0.0.1"), port=int(os.getenv("APP_PORT","5001")), use_reloader=False)
PY
  echo $! > "$PID_FILE"
  if wait_http_ok "${BASE_URL}/healthz" 100 0.25; then
    ok "✅ Сервер поднялся"
  else
    bad "❌ Не дождался ${BASE_URL}/healthz"
    exit 1
  fi
}

cleanup(){ kill_if_running; }
trap cleanup EXIT INT TERM

# ---------- Запуск сервера (если не --fast) ----------
if [[ "$FAST" == false ]]; then
  start_server
fi

# ---------- Прогон тестов ----------
TOTAL=0; PASS=0; FAIL=()

run_pytest () {
  local name="$1"; local path="$2"; shift 2 || true
  local extra_args="${*:-}"
  ((TOTAL++))
  echo; warn "📋 ${name}"; echo "-----------------------------------"
  if pytest "$path" -v --tb=short $extra_args; then
    ok "✅ ${name}: PASSED"; ((PASS++))
  else
    bad "❌ ${name}: FAILED"; FAIL+=("${name}"); return 1
  fi
}

# API
if [[ "$SUITE" == "api" || "$SUITE" == "all" ]]; then
  run_pytest "API Tests" "tests/api/" "--maxfail=5" || true
fi

# Smoke (минимальная проверка без браузера)
if [[ "$SUITE" == "smoke" || "$SUITE" == "all" ]]; then
  ((TOTAL++))
  echo; warn "📋 Smoke validation"; echo "-----------------------------------"
  if python - <<'PY'
import os
from app import create_app
try:
    app = create_app(os.getenv("APP_CONFIG","testing"))
except TypeError:
    app = create_app()
with app.test_client() as c:
    r = c.get("/healthz"); assert r.status_code == 200, f"healthz failed: {r.status_code}"
    r = c.get("/auth/login", follow_redirects=True); assert r.status_code == 200, f"login page failed: {r.status_code}"
print("Smoke OK")
PY
  then
    ok "✅ Smoke: READY"; ((PASS++))
  else
    bad "❌ Smoke: FAILED"; FAIL+=("Smoke")
  fi
fi

# E2E (опционально, если есть Chrome/Chromium)
if [[ "$RUN_E2E" == true && ("$SUITE" == "e2e" || "$SUITE" == "all") ]]; then
  if command -v google-chrome >/dev/null || command -v chromium-browser >/dev/null || command -v chromium >/dev/null; then
    export BASE_URL="$BASE_URL"
    run_pytest "E2E Tests" "tests/e2e/" "--maxfail=3" || true
  else
    warn "⚠️  Пропускаю E2E — нет Chrome/Chromium"
  fi
fi

# ---------- Итоги ----------
echo
echo "=================================="
warn "📊 TEST SUMMARY"
echo "=================================="
echo "Total suites: $TOTAL"
echo "Passed:      $PASS"
echo "Failed:      $((TOTAL-PASS))"
if [[ ${#FAIL[@]} -eq 0 ]]; then
  ok "🎉 ALL TESTS PASSED — ready to deploy"
  exit 0
else
  bad "❌ FAILED SUITES:"
  for s in "${FAIL[@]}"; do echo "   - $s"; done
  echo
  bad "🚫 DO NOT DEPLOY"
  exit 1
fi
