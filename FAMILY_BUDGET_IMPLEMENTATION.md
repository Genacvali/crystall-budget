# Реализация семейного доступа к расходам

## ✅ Выполнено

### 1. База данных
- ✅ Добавлено поле `shared_budget_id` в таблицы `expenses` и `categories`
- ✅ Создана и применена миграция `515954c99c28_add_shared_budget_support.py`
- ✅ Foreign key ссылки на `shared_budgets` таблицу

### 2. Модели (app/modules/budget/models.py)
**Expense model:**
- ✅ Добавлено поле `shared_budget_id`
- ✅ Метод `is_shared` - проверка принадлежности к семейному бюджету
- ✅ Метод `belongs_to_user(user_id)` - проверка доступа для просмотра
- ✅ Метод `can_edit(user_id)` - проверка прав на редактирование
  - Owner может редактировать
  - Members могут редактировать
  - Viewers не могут редактировать

**Category model:**
- ✅ Добавлено поле `shared_budget_id`

### 3. Сервисный слой (app/modules/budget/service.py)
**BudgetService:**
- ✅ `add_expense()` - добавлен параметр `shared_budget_id`
- ✅ `get_shared_budget_expenses()` - получение расходов семейного бюджета
- ✅ `get_user_accessible_expenses()` - получение всех доступных расходов (личные + семейные)
- ✅ `update_expense()` - с проверкой прав доступа
- ✅ `delete_expense()` - с проверкой прав доступа
- ✅ `get_shared_budget_categories()` - категории семейного бюджета

**Инвалидация кэша:**
- ✅ При изменении семейных расходов кэш инвалидируется для всех участников

### 4. Существующая инфраструктура
**Модели (app/modules/goals/models.py):**
- ✅ `SharedBudget` - семейный бюджет с кодом приглашения
- ✅ `SharedBudgetMember` - участники с ролями (owner, member, viewer)

**Сервисы (app/modules/goals/service.py):**
- ✅ `SharedBudgetService.create_shared_budget()` - создание
- ✅ `SharedBudgetService.join_shared_budget()` - присоединение по коду
- ✅ `SharedBudgetService.get_user_shared_budgets()` - список бюджетов пользователя
- ✅ `SharedBudgetService.remove_member()` - удаление участника
- ✅ `SharedBudgetService.update_member_role()` - изменение роли

**Роуты (app/modules/goals/routes.py):**
- ✅ `/goals/shared-budgets` - список семейных бюджетов
- ✅ `/goals/shared-budgets/create` - создание
- ✅ `/goals/shared-budgets/join` - присоединение
- ✅ `/goals/shared-budgets/<id>` - детали бюджета

### 5. Роуты для семейных расходов (app/modules/budget/routes.py)
- ✅ `/shared/<int:budget_id>/expenses` - список расходов семейного бюджета
- ✅ `/shared/<int:budget_id>/expenses/add` - добавление расхода
- ✅ `/set-active-budget` - переключение активного бюджета
- ✅ `/shared/<int:budget_id>/categories/add` - добавление категории в семейный бюджет

### 6. Шаблоны
- ✅ Создан `templates/budget/shared_expenses.html` - страница семейных расходов с:
  - Отображением участников бюджета и их ролей
  - Списком расходов с указанием автора
  - Формой добавления (только для member/owner)
  - Кнопками редактирования/удаления (только для member/owner)
  - Фильтром по датам
  - Мобильной версией с карточками

### 7. API методы
- ✅ Добавлен метод `to_dict()` в модель Expense для API-сериализации

### 8. Документация
- ✅ Создан `FAMILY_BUDGET_TESTING.md` с подробными сценариями тестирования

## 📋 Опциональные доработки (не критично)

### Обновление dashboard для переключения бюджетов
В `dashboard()` route можно добавить:

```python
# Получить активный бюджет из сессии
active_budget_id = session.get('active_budget')

if active_budget_id:
    # Показать семейный бюджет
    expenses = BudgetService.get_shared_budget_expenses(active_budget_id, user_id, year_month)
    categories = BudgetService.get_shared_budget_categories(active_budget_id, user_id)
else:
    # Показать личный бюджет
    expenses = BudgetService.get_user_accessible_expenses(user_id, year_month)
    categories = BudgetService.get_user_categories(user_id)

# Передать в шаблон
budgets = SharedBudgetService.get_user_shared_budgets(user_id)
```

### Обновление templates/budget/dashboard.html
Добавить selector бюджета:

```html
<div class="budget-selector mb-3">
    <select name="active_budget" onchange="this.form.submit()" class="form-select">
        <option value="personal" {% if not active_budget_id %}selected{% endif %}>
            💼 Личный бюджет
        </option>
        {% for budget in user_budgets %}
        <option value="{{ budget.id }}" {% if active_budget_id == budget.id %}selected{% endif %}>
            👨‍👩‍👧‍👦 {{ budget.name }}
        </option>
        {% endfor %}
    </select>
</div>
```

### API Endpoints (опционально)

```python
@api_v1_bp.route('/budgets/shared/<int:budget_id>/expenses', methods=['GET'])
@login_required
def get_shared_expenses_api(budget_id):
    """API: получить расходы семейного бюджета."""
    user_id = session['user_id']
    year_month = YearMonth.current()  # или из параметров

    expenses = BudgetService.get_shared_budget_expenses(budget_id, user_id, year_month)

    return jsonify({
        'expenses': [exp.to_dict() for exp in expenses]
    })

@api_v1_bp.route('/expenses/<int:expense_id>', methods=['PUT'])
@login_required
def update_expense_api(expense_id):
    """API: обновить расход."""
    user_id = session['user_id']
    data = request.get_json()

    expense = BudgetService.update_expense(
        expense_id=expense_id,
        user_id=user_id,
        amount=data.get('amount'),
        description=data.get('description'),
        category_id=data.get('category_id')
    )

    if not expense:
        return jsonify({'error': 'Нет прав или расход не найден'}), 403

    return jsonify(expense.to_dict())

@api_v1_bp.route('/expenses/<int:expense_id>', methods=['DELETE'])
@login_required
def delete_expense_api(expense_id):
    """API: удалить расход."""
    user_id = session['user_id']

    if BudgetService.delete_expense(expense_id, user_id):
        return jsonify({'success': True})

    return jsonify({'error': 'Нет прав или расход не найден'}), 403
```

## 🧪 Тестирование

После реализации протестировать:

1. **Создание семейного бюджета**
   - Создать бюджет
   - Получить код приглашения
   - Присоединиться вторым пользователем

2. **Добавление расходов**
   - Owner добавляет расход
   - Member добавляет расход
   - Viewer не может добавить (проверить)

3. **Редактирование расходов**
   - Owner может редактировать любой расход
   - Member может редактировать любой расход
   - Viewer не может редактировать

4. **Просмотр**
   - Все участники видят все расходы
   - Видно кто добавил расход

5. **Кэш**
   - При изменении расхода кэш инвалидируется у всех участников

## 📊 Архитектура

```
Пользователь A (Owner)     Пользователь B (Member)     Пользователь C (Viewer)
       |                            |                            |
       v                            v                            v
    Может:                       Может:                      Может:
    - Создавать расходы         - Создавать расходы         - Просматривать
    - Редактировать             - Редактировать
    - Удалять                   - Удалять
    - Управлять участниками
       |                            |                            |
       +----------------------------+----------------------------+
                                    |
                                    v
                          Семейный бюджет (shared_budget_id)
                                    |
                                    v
                          Общие расходы (Expense)
                          Общие категории (Category)
```

## 🔒 Безопасность

- ✅ Проверка прав через `expense.can_edit(user_id)`
- ✅ Проверка членства через `SharedBudgetMember`
- ✅ Разделение прав: owner, member, viewer
- ✅ Личные расходы (shared_budget_id=NULL) видят только их авторы
- ✅ Семейные расходы видят все участники бюджета
