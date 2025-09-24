# CrystalBudget Test Suite

Комплексная система тестирования для приложения управления бюджетом.

## Структура тестов

```
tests/
├── smoke/                 # Ручные смоки-тесты (15 мин)
│   └── manual_checklist.md
├── e2e/                   # E2E тесты с Playwright
│   ├── conftest.py
│   └── test_golden_path.py
├── api/                   # API тесты с pytest + requests  
│   ├── conftest.py
│   └── test_api_crud.py
└── README.md             # Эта документация
```

## Типы тестов

### 1. 🧪 Smoke Tests (Смоки-тесты)
**Время**: 15 минут  
**Тип**: Ручные  
**Цель**: Проверка критичного функционала после деплоя

**Золотой путь**:
```
Логин → Дашборд → Добавить доход → Добавить расход → 
Сменить месяц → Сменить тему → Логаут
```

**Запуск**: Следуйте чек-листу в `tests/smoke/manual_checklist.md`

### 2. 🤖 E2E Tests (End-to-End)
**Тип**: Автоматизированные (Playwright)  
**Браузеры**: Chrome, Firefox, Safari, Mobile  
**Цель**: Полная автоматизация пользовательских сценариев

**Покрытие**:
- Полный золотой путь пользователя
- Мобильная адаптивность
- Обработка ошибок (404, валидация форм)
- Кроссбраузерная совместимость

### 3. 🔌 API Tests
**Тип**: Автоматизированные (pytest + requests)  
**Цель**: CRUD операции и валидация API

**Покрытие**:
- Расходы: CRUD, фильтрация, пагинация
- Доходы: CRUD, валидация
- Категории: CRUD, связи с расходами
- Пагинация и производительность
- Обработка ошибок и валидация

## Быстрый старт

### Установка зависимостей
```bash
# Основные зависимости
pip install -r requirements.txt

# Тестовые зависимости  
pip install -r requirements-test.txt

# Playwright (для E2E)
playwright install chromium
```

### Запуск всех тестов
```bash
# Через удобный скрипт
./scripts/run-tests.sh

# Или напрямую через pytest
pytest tests/ -v
```

### Запуск конкретного типа тестов
```bash
# Только API тесты
./scripts/run-tests.sh --suite api

# Только E2E тесты  
./scripts/run-tests.sh --suite e2e

# Только smoke валидация
./scripts/run-tests.sh --suite smoke
```

## CI/CD интеграция

### GitHub Actions
Автоматический запуск при:
- Push в main/develop
- Pull Request  
- Ручной запуск (workflow_dispatch)

**Pipeline**:
1. ✅ API Tests
2. ✅ E2E Tests  
3. ✅ Smoke Test Validation
4. ✅ Security Check
5. ✅ Deployment Readiness Report

### Статус деплоя
```bash
# ✅ Все тесты прошли
"🎉 Ready for deployment"

# ❌ Есть падающие тесты  
"🚫 DO NOT DEPLOY - Fix failing tests"
```

## Локальная разработка

### Быстрая проверка
```bash
# Минимальная проверка перед коммитом
pytest tests/api/test_api_crud.py::TestExpensesAPI::test_create_expense -v

# Smoke test validation
python -c "from app import create_app; app = create_app(); print('✅ App starts OK')"
```

### Отладка тестов
```bash  
# С подробным выводом
./scripts/run-tests.sh --verbose

# Остановка на первой ошибке
./scripts/run-tests.sh --stop-on-fail

# Конкретный тест
pytest tests/e2e/test_golden_path.py::TestGoldenPath::test_smoke_golden_path -v -s
```

### Переменные окружения
```bash
# Тестовая база данных
export BUDGET_DB="sqlite:///test_local.db"

# Секретный ключ для тестов  
export SECRET_KEY="test-secret-key"

# URL для E2E тестов
export BASE_URL="http://localhost:5000"
```

## Создание новых тестов

### API тест
```python
def test_new_feature(self, api_client, helpers):
    response = api_client.post('/api/v1/new-endpoint', json={'data': 'test'})
    helpers.assert_response_success(response, 201)
    
    data = response.json()
    helpers.assert_json_structure(data, ['id', 'created_at'])
```

### E2E тест  
```python
@pytest.mark.asyncio
async def test_new_flow(self, page, helpers):
    await page.goto('/new-feature')
    await helpers.wait_for_load(page)
    
    await page.click('button:has-text("New Action")')
    await expect(page.locator('.success-message')).to_be_visible()
```

## Отчёты

### Coverage Report
```bash
pytest --cov=app --cov-report=html
# Откройте htmlcov/index.html
```

### E2E Screenshots & Videos
```bash
# При падении E2E тестов
ls test-results/screenshots/
ls test-results/videos/
```

### CI Artifacts
- E2E screenshots при ошибках
- Playwright HTML отчёт
- Bandit security report  
- Coverage reports

## Troubleshooting

### E2E тесты не работают
```bash
# Проверить Chrome/Chromium
which google-chrome chromium-browser chromium

# Установить Playwright browsers
playwright install --with-deps chromium

# Проверить приложение запускается
export BUDGET_DB="sqlite:///debug.db"
python app.py
```

### API тесты падают
```bash
# Проверить тестовую БД
ls -la test_*.db

# Пересоздать БД
rm test_*.db && python -c "from app import create_app; from app.core.extensions import db; app = create_app(); app.app_context().push(); db.create_all()"

# Проверить миграции
flask db current
```

### Smoke тесты
```bash
# Проверить структуру
ls -la tests/smoke/

# Проверить чек-лист  
cat tests/smoke/manual_checklist.md

# Запуск на продакшене
curl https://your-domain/healthz
```

## Качественные критерии

### API Coverage
- ✅ CRUD операции для всех основных сущностей
- ✅ Валидация входных данных
- ✅ Обработка ошибок (400, 401, 404, 500)
- ✅ Пагинация и фильтрация
- ✅ Производительность (< 2 сек)

### E2E Coverage  
- ✅ Золотой путь пользователя (логин → основные действия → логаут)
- ✅ Мобильная адаптивность
- ✅ Кроссбраузерность (Chrome, Firefox, Safari)
- ✅ Обработка ошибок UI

### Smoke Coverage
- ✅ Критичные функции работают
- ✅ Нет блокеров для пользователей  
- ✅ Быстрая диагностика проблем (15 мин)

## Production Readiness

### Pre-Deploy
1. ✅ Все автотесты проходят
2. ✅ Manual smoke tests выполнены  
3. ✅ Security check пройден
4. ✅ Database backup создан

### Post-Deploy
1. ✅ Smoke tests на продакшене  
2. ✅ Monitoring активен (1 час)
3. ✅ Performance metrics в норме
4. ✅ Telegram auth работает

### Rollback Criteria
- ❌ Критичные функции не работают
- ❌ Высокий error rate (>5%)
- ❌ Performance деградация (>2x)
- ❌ Security инциденты