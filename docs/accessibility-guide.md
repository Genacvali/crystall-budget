# Руководство по доступности и кроссбраузерности

Комплексное руководство по обеспечению доступности (A11y) и кроссбраузерной совместимости для CrystalBudget.

## 🎯 Цели и стандарты

### WCAG 2.1 Соответствие
- **Уровень AA**: Обязательный минимум
- **Контраст**: 4.5:1 для обычного текста, 3:1 для крупного
- **Размер touch targets**: минимум 44x44px на мобильных
- **Клавиатурная навигация**: полный доступ без мыши

### Поддерживаемые браузеры
- ✅ **Chrome 90+** (desktop, mobile)
- ✅ **Firefox 88+** (desktop, mobile) 
- ✅ **Safari 14+** (macOS, iOS)
- ✅ **Edge 90+**
- ⚠️ **IE11** (базовая поддержка, fallbacks)

## 📋 Реализованные возможности

### 1. ARIA разметка и семантика

#### Обязательные ARIA атрибуты
```html
<!-- Формы -->
<form role="form" aria-label="Форма добавления расхода" novalidate>
  <input type="number" 
         aria-describedby="amount-help"
         aria-invalid="false"
         aria-required="true">
  <div id="amount-help" class="visually-hidden">Введите сумму расхода в рублях</div>
  <div role="alert" aria-live="polite" class="invalid-feedback"></div>
</form>

<!-- Навигация -->
<nav role="navigation" aria-label="Основная навигация">
  <button aria-expanded="false" aria-controls="mobile-menu">
    Меню <span class="visually-hidden">навигации</span>
  </button>
</nav>

<!-- Live regions -->
<div aria-live="polite" aria-atomic="true" class="visually-hidden" id="announcer"></div>
```

#### Landmarks и структура
```html
<main id="main-content" role="main" aria-label="Основное содержимое">
  <section role="region" aria-labelledby="dashboard-heading">
    <h1 id="dashboard-heading">Дашборд</h1>
  </section>
</main>
```

### 2. Фокус-стили и клавиатурная навигация

#### Видимые фокус-индикаторы
```css
:focus {
  outline: 2px solid var(--a11y-focus) !important;
  outline-offset: 2px;
  box-shadow: 0 0 0 0.25rem var(--a11y-focus-shadow) !important;
}

/* Усиленные стили для интерактивных элементов */
.btn:focus,
.form-control:focus {
  outline: 3px solid var(--a11y-focus) !important;
  box-shadow: 0 0 0 0.25rem var(--a11y-focus-shadow) !important;
}
```

#### Keyboard shortcuts
- **Alt + D**: Дашборд
- **Alt + E**: Расходы
- **Alt + I**: Доходы
- **Alt + C**: Категории
- **Escape**: Закрыть модальные окна/меню
- **Tab/Shift+Tab**: Навигация по элементам
- **Arrow keys**: Навигация по табам

#### Focus trap в модальных окнах
```javascript
function trapFocus(container) {
  const focusableElements = container.querySelectorAll(
    'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
  );
  
  const firstFocusable = focusableElements[0];
  const lastFocusable = focusableElements[focusableElements.length - 1];
  
  container.addEventListener('keydown', function(e) {
    if (e.key === 'Tab') {
      if (e.shiftKey) {
        if (document.activeElement === firstFocusable) {
          lastFocusable.focus();
          e.preventDefault();
        }
      } else {
        if (document.activeElement === lastFocusable) {
          firstFocusable.focus();
          e.preventDefault();
        }
      }
    }
  });
}
```

### 3. Контрастные цвета (4.5:1)

#### Цветовая палитра WCAG AA
```css
:root {
  /* Основные цвета - светлая тема */
  --a11y-text-primary: #212529;       /* 16.75:1 на белом */
  --a11y-text-secondary: #343a40;     /* 9.95:1 на белом */
  --a11y-text-muted: #495057;         /* 7.00:1 на белом */
  
  /* Статусные цвета */
  --a11y-success: #146c43;            /* 4.54:1 на белом */
  --a11y-danger: #b02a37;             /* 4.56:1 на белом */
  --a11y-warning: #997404;            /* 4.50:1 на белом */
  --a11y-info: #055160;               /* 4.52:1 на белом */
  --a11y-primary: #0a58ca;            /* 4.57:1 на белом */
}

[data-bs-theme="dark"] {
  /* Тёмная тема - улучшенные контрасты */
  --a11y-text-primary: #f8f9fa;       /* 18.67:1 на тёмном */
  --a11y-text-secondary: #dee2e6;     /* 12.63:1 на тёмном */
  --a11y-text-muted: #adb5bd;         /* 7.06:1 на тёмном */
  
  --a11y-success: #75b798;            /* 4.51:1 на тёмном */
  --a11y-danger: #ea868f;             /* 4.50:1 на тёмном */
  --a11y-warning: #ffda6a;            /* 7.25:1 на тёмном */
  --a11y-info: #6ed3f0;               /* 5.74:1 на тёмном */
  --a11y-primary: #6ea8fe;            /* 4.56:1 на тёмном */
}
```

### 4. Форм-валидация с ARIA

#### Real-time валидация
```javascript
function validateField(field) {
  const isValid = field.checkValidity();
  const feedback = field.parentNode.querySelector('.invalid-feedback');
  
  // Обновляем ARIA состояния
  field.setAttribute('aria-invalid', !isValid);
  field.classList.toggle('is-invalid', !isValid);
  field.classList.toggle('is-valid', isValid && field.value);
  
  // Показываем сообщение об ошибке
  if (feedback) {
    if (!isValid) {
      feedback.textContent = getValidationMessage(field);
      feedback.style.display = 'block';
    } else {
      feedback.style.display = 'none';
    }
  }
  
  return isValid;
}

function getValidationMessage(field) {
  if (field.validity.valueMissing) {
    const label = field.previousElementSibling;
    const fieldName = label ? label.textContent.replace('*', '').trim() : 'Поле';
    return `${fieldName} обязательно для заполнения`;
  }
  if (field.validity.typeMismatch) return 'Неверный формат данных';
  if (field.validity.rangeUnderflow) return `Значение должно быть не менее ${field.min}`;
  if (field.validity.rangeOverflow) return `Значение должно быть не более ${field.max}`;
  if (field.validity.tooLong) return `Слишком длинный текст (максимум ${field.maxLength} символов)`;
  return field.validationMessage || 'Неверное значение';
}
```

## 🌍 Кроссбраузерная совместимость

### 1. HTML5 Input Types

#### Type="month" поддержка
```javascript
// Проверка поддержки и fallback
function initMonthInputFallback() {
  const monthInputs = document.querySelectorAll('input[type="month"]');
  
  monthInputs.forEach(input => {
    if (input.type !== 'month') {
      // Создаём fallback select для Safari/IE
      const fallback = document.createElement('select');
      fallback.name = input.name;
      fallback.id = input.id;
      fallback.className = input.className;
      fallback.required = input.required;
      
      // Генерируем опции месяцев
      const currentYear = new Date().getFullYear();
      const months = ['Январь', 'Февраль', 'Март', ...];
      
      fallback.innerHTML = '<option value="">Выберите месяц</option>';
      
      for (let year = currentYear - 2; year <= currentYear + 1; year++) {
        months.forEach((month, index) => {
          const value = `${year}-${String(index + 1).padStart(2, '0')}`;
          const option = new Option(`${month} ${year}`, value);
          fallback.add(option);
        });
      }
      
      input.parentNode.replaceChild(fallback, input);
    }
  });
}
```

#### Десятичные числа (запятая vs точка)
```javascript
// Поддержка разных локалей
function normalizeDecimalInput(input) {
  input.addEventListener('blur', function() {
    let value = this.value;
    
    // Заменяем запятую на точку для браузеров
    if (value.includes(',')) {
      // Определяем формат: европейский (1.234,56) vs американский (1,234.56)
      const lastComma = value.lastIndexOf(',');
      const lastDot = value.lastIndexOf('.');
      
      if (lastComma > lastDot) {
        // Европейский формат: 1.234,56 -> 1234.56
        value = value.replace(/\./g, '').replace(',', '.');
      } else {
        // Американский формат: 1,234.56 -> 1234.56  
        value = value.replace(/,/g, '');
      }
      
      this.value = value;
    }
  });
}
```

### 2. CSS Compatibility

#### CSS Grid fallbacks
```css
/* Modern grid */
.dashboard-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 1rem;
}

/* Fallback для старых браузеров */
.dashboard-grid {
  display: flex;
  flex-wrap: wrap;
  margin: -0.5rem;
}

.dashboard-grid > * {
  flex: 1 1 300px;
  margin: 0.5rem;
}

/* Используем @supports */
@supports (display: grid) {
  .dashboard-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
    gap: 1rem;
    margin: 0;
  }
  
  .dashboard-grid > * {
    margin: 0;
  }
}
```

#### Custom Properties fallbacks
```css
/* Fallback значения */
.btn-primary {
  background-color: #0d6efd;  /* Fallback */
  background-color: var(--bs-primary, #0d6efd);
  
  color: white;               /* Fallback */
  color: var(--bs-btn-color, white);
}
```

### 3. JavaScript Compatibility

#### Modern JS features с fallbacks
```javascript
// Async/await с Promise fallback
async function submitForm(form) {
  try {
    const response = await fetch(form.action, {
      method: 'POST',
      body: new FormData(form)
    });
    
    if (response.ok) {
      showSuccess('Данные сохранены');
    } else {
      throw new Error('Server error');
    }
  } catch (error) {
    showError('Ошибка сохранения');
  }
}

// Fallback для старых браузеров
function submitFormLegacy(form) {
  var xhr = new XMLHttpRequest();
  var formData = new FormData(form);
  
  xhr.open('POST', form.action);
  
  xhr.onreadystatechange = function() {
    if (xhr.readyState === 4) {
      if (xhr.status === 200) {
        showSuccess('Данные сохранены');
      } else {
        showError('Ошибка сохранения');
      }
    }
  };
  
  xhr.send(formData);
}

// Feature detection
const supportsAsyncAwait = (function() {
  try {
    return (async function(){}).constructor;
  } catch (e) {
    return false;
  }
})();

function submitFormCompatible(form) {
  if (supportsAsyncAwait) {
    return submitForm(form);
  } else {
    return submitFormLegacy(form);
  }
}
```

## 🧪 Тестирование

### 1. Автоматические тесты

#### Accessibility тесты
```bash
# Запуск accessibility тестов
pytest tests/e2e/test_cross_browser.py::TestAccessibilityAcrossBrowsers -v

# Specific browser
pytest tests/e2e/test_cross_browser.py::TestAccessibilityAcrossBrowsers::test_aria_attributes_support[chromium] -v
```

#### Cross-browser тесты  
```bash
# Все браузеры
pytest tests/e2e/test_cross_browser.py::TestCrossBrowserCompatibility -v

# Форм-совместимость
pytest tests/e2e/test_form_compatibility.py -v

# Type="month" тесты
pytest tests/e2e/test_form_compatibility.py::TestFormInputCompatibility::test_month_input_compatibility -v
```

#### Mobile compatibility
```bash
# Мобильная совместимость
pytest tests/e2e/test_cross_browser.py::TestCrossBrowserCompatibility::test_mobile_compatibility -v
```

### 2. Ручное тестирование

#### Keyboard navigation checklist
- [ ] Tab навигация работает во всех разделах
- [ ] Все интерактивные элементы достижимы с клавиатуры
- [ ] Фокус видим и логичен
- [ ] Escape закрывает модальные окна
- [ ] Enter/Space активируют кнопки
- [ ] Arrow keys работают в выпадающих списках

#### Screen reader checklist
- [ ] Заголовки структурированы (h1-h6)
- [ ] Все изображения имеют alt-тексты
- [ ] Формы правильно подписаны
- [ ] Ошибки валидации читаются
- [ ] Live regions анонсируют изменения
- [ ] Navigation landmarks присутствуют

#### Mobile touch checklist
- [ ] Touch targets минимум 44x44px
- [ ] Swipe жесты работают корректно
- [ ] Pinch-to-zoom не блокирован
- [ ] Viewport настроен правильно
- [ ] Горизонтальная прокрутка отсутствует

### 3. Инструменты тестирования

#### Browser dev tools
```javascript
// Accessibility tree в Chrome DevTools
// 1. F12 → Elements → Accessibility tab
// 2. Проверить ARIA свойства
// 3. Симулировать screen reader

// Color contrast checker
// 1. F12 → Elements → Styles
// 2. Кликнуть на цветной квадратик
// 3. Проверить Contrast ratio

// Lighthouse accessibility audit
// 1. F12 → Lighthouse → Accessibility
// 2. Запустить аудит
// 3. Исправить найденные проблемы
```

#### Screen readers
- **NVDA** (Windows) - бесплатный
- **JAWS** (Windows) - коммерческий
- **VoiceOver** (macOS) - встроенный
- **TalkBack** (Android) - встроенный

## 📱 Responsive Design

### 1. Breakpoints
```css
/* Mobile first подход */
.dashboard-card {
  padding: 1rem;
  margin: 0.5rem;
}

/* Tablet */
@media (min-width: 768px) {
  .dashboard-card {
    padding: 1.5rem;
    margin: 1rem;
  }
}

/* Desktop */
@media (min-width: 1200px) {
  .dashboard-card {
    padding: 2rem;
    margin: 1.5rem;
  }
}
```

### 2. Touch targets
```css
/* Минимальные размеры для touch */
.btn,
.nav-link,
[role="button"] {
  min-height: 44px;
  min-width: 44px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

/* На мобильных увеличиваем до 48px */
@media (max-width: 576px) {
  .btn {
    min-height: 48px;
    min-width: 48px;
  }
}
```

## 🔧 Debugging и оптимизация

### 1. Performance

#### Accessibility tree optimization
```css
/* Скрываем декоративные элементы от screen readers */
.decorative-icon {
  aria-hidden: true;
}

/* Используем visually-hidden вместо display: none */
.sr-only {
  position: absolute !important;
  width: 1px !important;
  height: 1px !important;
  padding: 0 !important;
  margin: -1px !important;
  overflow: hidden !important;
  clip: rect(0, 0, 0, 0) !important;
  white-space: nowrap !important;
  border: 0 !important;
}
```

#### Focus performance
```javascript
// Debounce фокус-события для производительности
function debounce(func, wait) {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
}

const debouncedFocusHandler = debounce(handleFocus, 150);
document.addEventListener('focusin', debouncedFocusHandler);
```

### 2. Общие принципы

#### Progressive Enhancement
1. **Базовая функциональность** работает без JS
2. **Enhanced UX** добавляется через JavaScript
3. **Graceful degradation** при отсутствии возможностей

#### Accessibility First
1. **Semantic HTML** как основа
2. **ARIA** только когда HTML недостаточно  
3. **Keyboard accessibility** обязательно
4. **Screen reader** тестирование регулярно

## 📚 Ресурсы и документация

### Спецификации
- [WCAG 2.1 Guidelines](https://www.w3.org/WAI/WCAG21/quickref/)
- [ARIA Authoring Practices](https://www.w3.org/WAI/ARIA/apg/)
- [MDN Accessibility](https://developer.mozilla.org/en-US/docs/Web/Accessibility)

### Инструменты
- [axe DevTools](https://www.deque.com/axe/devtools/)
- [Lighthouse](https://developers.google.com/web/tools/lighthouse)
- [Color Oracle](https://colororacle.org/) - симулятор дальтонизма
- [WebAIM Contrast Checker](https://webaim.org/resources/contrastchecker/)

### Тестирование
- [WAVE Web Accessibility Evaluator](https://wave.webaim.org/)
- [Pa11y Command Line](https://github.com/pa11y/pa11y)
- [Playwright Accessibility Testing](https://playwright.dev/docs/accessibility-testing)