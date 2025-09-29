# CrystalBudget Modal System

Унифицированная система модальных окон для консистентного UX по всему приложению.

## Архитектура

### Компоненты системы

1. **CSS** - `static/css/components/modal.css`
   - Стили для всех типов модалок
   - Responsive дизайн с мобильной оптимизацией
   - Темная/светлая тема
   - Анимации и переходы

2. **JavaScript** - `static/js/modals.js`
   - Управление показом/скрытием модалок
   - AJAX загрузка контента
   - Управление фокусом и доступностью
   - Confirm-диалоги

3. **Templates** - `templates/components/_modal.html`
   - Jinja2 макросы для разных типов модалок
   - Переиспользуемые компоненты форм

4. **Partials** - `templates/components/modals/`
   - Отдельные шаблоны для контента модалок
   - Загружаются по требованию через AJAX

## Использование

### 1. Базовая модалка

```html
<!-- Триггер -->
<button data-modal-open="#my-modal">Открыть модалку</button>

<!-- Модалка -->
{% from 'components/_modal.html' import modal %}
{{ modal('my-modal', 'Заголовок', 'Содержимое модалки') }}
```

### 2. Модалка с AJAX загрузкой

```html
<!-- Триггер -->
<button data-modal-url="/categories/add/modal" 
        data-modal-target="modal-form">
  Добавить категорию
</button>

<!-- Контейнер (создается автоматически) -->
<!-- Содержимое загружается с сервера -->
```

### 3. Confirm-диалог

```html
<!-- Триггер -->
<button data-confirm="Удалить категорию?"
        data-confirm-action="deleteCategory(123)">
  Удалить
</button>

<!-- JavaScript -->
<script>
function deleteCategory(id) {
  // Логика удаления
  fetch('/categories/' + id + '/delete', {method: 'POST'})
    .then(() => window.location.reload());
}
</script>
```

### 4. Форма в модалке

```html
{% from 'components/_modal.html' import modal_form %}
{{ modal_form(
  'form-modal',
  'Заголовок формы',
  '/submit/url',
  form_content,
  submit_text='Сохранить'
) }}
```

## JavaScript API

### Открытие/закрытие

```javascript
// Открыть модалку
Modal.show('modal-id');

// Закрыть модалку
Modal.hide(); // текущую
Modal.hide('modal-id'); // конкретную

// Закрыть все
Modal.closeAll();
```

### AJAX загрузка

```javascript
// Загрузить и показать
Modal.load('modal-id', '/path/to/content');

// С опциями
Modal.load('modal-id', '/path', {
  size: 'lg',
  onLoad: () => console.log('Загружено')
});
```

### Confirm диалоги

```javascript
// Простой confirm
Modal.confirm('Удалить?', () => {
  console.log('Подтверждено');
});

// С опциями
Modal.confirm('Удалить файл?', deleteFile, {
  title: 'Подтверждение',
  confirmText: 'Удалить',
  cancelText: 'Отмена',
  type: 'danger'
});
```

### События

```javascript
// Слушать события модалок
document.addEventListener('Modal:opened', (e) => {
  console.log('Открыта:', e.detail.modalId);
});

document.addEventListener('Modal:closed', (e) => {
  console.log('Закрыта:', e.detail.modalId);
});

document.addEventListener('Modal:loaded', (e) => {
  console.log('Загружена:', e.detail.url);
});
```

## Серверная часть

### Роуты для partial'ов

```python
@bp.route('/categories/add/modal')
def category_add_modal():
    return render_template('components/modals/_category_add.html',
                         income_sources=get_income_sources())

@bp.route('/categories/<int:cat_id>/edit/modal')
def category_edit_modal(cat_id):
    category = Category.query.get_or_404(cat_id)
    return render_template('components/modals/_category_edit.html',
                         category=category,
                         income_sources=get_income_sources())
```

### Обработка форм

```python
@bp.route('/categories/add', methods=['POST'])
def categories_add():
    # Обработка формы
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        # AJAX запрос - вернуть JSON или redirect header
        return '', 200, {'X-Redirect': url_for('budget.categories')}
    else:
        # Обычный запрос - redirect
        return redirect(url_for('budget.categories'))
```

## Типы модалок

### 1. Размеры

- `cb-modal--sm` - маленькие (400px)
- `cb-modal--md` - средние (500px, по умолчанию)
- `cb-modal--lg` - большие (700px)
- `cb-modal--xl` - очень большие (900px)
- `cb-modal--fullscreen` - на весь экран

### 2. Режимы

- `cb-modal--sheet` - мобильная "шторка"
- `cb-modal--form` - оптимизированная для форм
- `cb-modal--confirm` - диалог подтверждения

### 3. Опции

- `cb-modal--no-backdrop` - без затемнения
- `cb-modal--no-close` - без кнопки закрытия
- `cb-modal--scrollable` - прокручиваемое содержимое

## Доступность

### Keyboard navigation

- `Esc` - закрыть модалку
- `Tab` - навигация внутри модалки
- `Enter` - активировать primary кнопку

### Screen readers

- `role="dialog"`
- `aria-modal="true"`
- `aria-labelledby` - связь с заголовком
- `aria-hidden` - скрытие от скрин-ридеров когда закрыта

### Focus management

- Фокус сохраняется и восстанавливается
- Фокус не уходит за пределы модалки
- Первый интерактивный элемент получает фокус

## Мобильная оптимизация

### Автоматические изменения

- Планшеты: модалки занимают больше места
- Мобильные: автоматически становятся "шторками"
- Очень маленькие экраны: полноэкранный режим

### Жесты

- Свайп вниз для закрытия "шторки"
- Тап по backdrop для закрытия

## Миграция со старых модалок

### 1. Удалить старые модалки

```html
<!-- УДАЛИТЬ -->
<div class="modal fade" id="oldModal">
  <!-- старая разметка -->
</div>

<!-- УДАЛИТЬ локальные стили -->
<style>
.modal-lg { /* удалить */ }
</style>

<!-- УДАЛИТЬ локальный JS -->
<script>
$('#oldModal').modal('show'); // удалить
</script>
```

### 2. Заменить триггеры

```html
<!-- БЫЛО -->
<button data-bs-toggle="modal" data-bs-target="#oldModal">

<!-- СТАЛО -->
<button data-modal-url="/path/to/modal">
```

### 3. Создать partial

```html
<!-- templates/components/modals/_my_modal.html -->
<div class="cb-modal__header">
  <h5 class="cb-modal__title">{{ title }}</h5>
  <button type="button" class="cb-modal__close" data-modal-close></button>
</div>

<div class="cb-modal__body">
  <!-- содержимое -->
</div>

<div class="cb-modal__footer">
  <div class="cb-modal__actions">
    <button class="cb-modal__btn cb-modal__btn--outline" data-modal-close>
      Отмена
    </button>
    <button class="cb-modal__btn cb-modal__btn--primary">
      Сохранить
    </button>
  </div>
</div>
```

### 4. Добавить роут

```python
@bp.route('/my-modal')
def my_modal():
    return render_template('components/modals/_my_modal.html')
```

## Лучшие практики

### 1. Именование

- ID модалок: `modal-{type}` (modal-form, modal-confirm)
- Partial'ы: `_model_action.html` (_category_add.html)
- Роуты: `{model}_{action}_modal` (category_add_modal)

### 2. Размеры

- Формы: `lg` для сложных, `md` для простых
- Confirm: всегда `sm`
- Таблицы/списки: `lg` или `xl`

### 3. Содержимое

- Используйте `form_section()` для группировки полей
- Sticky header/footer для длинных форм
- Loading состояния для AJAX

### 4. Производительность

- Создавайте модалки по требованию
- Убирайте из DOM после закрытия
- Переиспользуйте контейнеры

## Troubleshooting

### Модалка не открывается

1. Проверьте подключение `modals.js`
2. Проверьте правильность data-атрибутов
3. Посмотрите консоль на ошибки

### AJAX не работает

1. Проверьте роут сервера
2. Убедитесь что возвращается HTML
3. Проверьте CSRF токены

### Стили ломаются

1. Убедитесь что `modal.css` подключен
2. Проверьте конфликты с Bootstrap
3. Используйте правильные CSS классы

### Проблемы с фокусом

1. Убедитесь в правильности aria-атрибутов
2. Проверьте tabindex значения
3. Тестируйте с клавиатурой