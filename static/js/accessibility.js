/**
 * Accessibility improvements for Crystal Budget
 * Улучшения доступности для Crystal Budget
 */

(function() {
    'use strict';
    
    // Инициализация после загрузки DOM
    document.addEventListener('DOMContentLoaded', function() {
        initAccessibilityFeatures();
    });
    
    function initAccessibilityFeatures() {
        initFocusManagement();
        initKeyboardNavigation();
        initAriaUpdates();
        initPreferredMotion();
        initHighContrast();
        initFormValidation();
        initSkipLinks();
    }
    
    /**
     * Управление фокусом для модальных окон и выпадающих меню
     */
    function initFocusManagement() {
        // Трапинг фокуса в модальных окнах
        const modals = document.querySelectorAll('.modal');
        modals.forEach(modal => {
            modal.addEventListener('shown.bs.modal', function() {
                trapFocus(modal);
                // Установить фокус на первый интерактивный элемент
                const firstFocusable = modal.querySelector('button, input, select, textarea, [tabindex]:not([tabindex="-1"])');
                if (firstFocusable) {
                    firstFocusable.focus();
                }
            });
            
            modal.addEventListener('hidden.bs.modal', function() {
                // Вернуть фокус на элемент, открывший модальное окно
                const trigger = document.querySelector('[data-bs-target="#' + modal.id + '"]');
                if (trigger) {
                    trigger.focus();
                }
            });
        });
        
        // Обновление aria-expanded для бургер-меню
        const drawerToggle = document.getElementById('openDrawer');
        const drawer = document.getElementById('drawer');
        
        if (drawerToggle && drawer) {
            const observer = new MutationObserver(function(mutations) {
                mutations.forEach(function(mutation) {
                    if (mutation.type === 'attributes' && mutation.attributeName === 'hidden') {
                        const isHidden = drawer.hasAttribute('hidden');
                        drawerToggle.setAttribute('aria-expanded', !isHidden);
                    }
                });
            });
            
            observer.observe(drawer, {
                attributes: true,
                attributeFilter: ['hidden']
            });
        }
    }
    
    /**
     * Трапинг фокуса внутри контейнера
     */
    function trapFocus(container) {
        const focusableElements = container.querySelectorAll(
            'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
        );
        
        if (focusableElements.length === 0) return;
        
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
    
    /**
     * Клавиатурная навигация
     */
    function initKeyboardNavigation() {
        // ESC для закрытия модальных окон и выпадающих меню
        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape') {
                // Закрыть открытые модальные окна
                const openModal = document.querySelector('.modal.show');
                if (openModal) {
                    const modal = bootstrap.Modal.getInstance(openModal);
                    if (modal) modal.hide();
                    return;
                }
                
                // Закрыть drawer
                const drawer = document.getElementById('drawer');
                if (drawer && !drawer.hasAttribute('hidden')) {
                    const closeBtn = document.getElementById('closeDrawer');
                    if (closeBtn) closeBtn.click();
                    return;
                }
                
                // Закрыть выпадающие меню
                const openDropdown = document.querySelector('.dropdown-menu.show');
                if (openDropdown) {
                    const dropdown = bootstrap.Dropdown.getInstance(openDropdown.previousElementSibling);
                    if (dropdown) dropdown.hide();
                }
            }
        });
        
        // Улучшение навигации по табам
        const tabs = document.querySelectorAll('.cb-tab');
        tabs.forEach((tab, index) => {
            tab.addEventListener('keydown', function(e) {
                if (e.key === 'ArrowRight' || e.key === 'ArrowLeft') {
                    e.preventDefault();
                    const nextIndex = e.key === 'ArrowRight' ? 
                        (index + 1) % tabs.length : 
                        (index - 1 + tabs.length) % tabs.length;
                    tabs[nextIndex].focus();
                }
            });
        });
    }
    
    /**
     * Обновление ARIA атрибутов
     */
    function initAriaUpdates() {
        // Обновление aria-checked для переключателей темы
        const themeToggle = document.getElementById('theme');
        if (themeToggle) {
            themeToggle.addEventListener('change', function() {
                this.setAttribute('aria-checked', this.checked);
            });
        }
        
        const drawerThemeToggle = document.getElementById('themeToggleDrawer');
        if (drawerThemeToggle) {
            drawerThemeToggle.addEventListener('click', function() {
                const checked = this.getAttribute('aria-checked') === 'true';
                this.setAttribute('aria-checked', !checked);
            });
        }
        
        // Анонсирование изменений для скрин-ридеров
        const announcer = createAnnouncer();
        
        // Анонсировать успешные действия
        document.addEventListener('click', function(e) {
            if (e.target.matches('.btn-success, .btn[type="submit"]')) {
                setTimeout(() => {
                    const message = document.querySelector('.alert-success');
                    if (message) {
                        announcer.announce(message.textContent.trim());
                    }
                }, 100);
            }
        });
    }
    
    /**
     * Создание элемента для анонсов скрин-ридерам
     */
    function createAnnouncer() {
        const announcer = document.createElement('div');
        announcer.setAttribute('aria-live', 'polite');
        announcer.setAttribute('aria-atomic', 'true');
        announcer.className = 'visually-hidden';
        document.body.appendChild(announcer);
        
        return {
            announce: function(message) {
                announcer.textContent = message;
                setTimeout(() => {
                    announcer.textContent = '';
                }, 1000);
            }
        };
    }
    
    /**
     * Поддержка prefers-reduced-motion
     */
    function initPreferredMotion() {
        if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
            // Отключить автоматические карусели и анимации
            const carousels = document.querySelectorAll('[data-bs-ride="carousel"]');
            carousels.forEach(carousel => {
                carousel.removeAttribute('data-bs-ride');
            });
            
            // Ускорить все анимации
            document.documentElement.style.setProperty('--animation-duration', '0.01ms');
        }
    }
    
    /**
     * Поддержка высокого контраста
     */
    function initHighContrast() {
        if (window.matchMedia('(prefers-contrast: high)').matches) {
            document.body.classList.add('high-contrast');
        }
    }
    
    /**
     * Утилита для логирования ошибок доступности в dev режиме
     */
    function logA11yIssues() {
        // Проверяем режим разработки через location или localStorage
        const isDevelopment = location.hostname === 'localhost' || 
                             location.hostname === '127.0.0.1' || 
                             localStorage.getItem('debug') === 'true';
        
        if (isDevelopment) {
            // Проверить наличие alt у изображений
            const images = document.querySelectorAll('img:not([alt])');
            if (images.length > 0) {
                console.warn('A11y: Найдены изображения без alt атрибута:', images);
            }
            
            // Проверить наличие label у form controls
            const inputs = document.querySelectorAll('input:not([aria-label]):not([aria-labelledby])');
            const unlabeledInputs = Array.from(inputs).filter(input => {
                return !document.querySelector('label[for="' + input.id + '"]');
            });
            
            if (unlabeledInputs.length > 0) {
                console.warn('A11y: Найдены поля формы без подписей:', unlabeledInputs);
            }
            
            // Проверить контрастность (упрощённая проверка)
            const buttons = document.querySelectorAll('.btn');
            buttons.forEach(button => {
                const styles = getComputedStyle(button);
                const bgColor = styles.backgroundColor;
                const textColor = styles.color;
                
                if (bgColor && textColor) {
                    // Здесь можно добавить более сложную проверку контрастности
                    console.debug('A11y: Проверка контрастности для кнопки:', button, {
                        background: bgColor,
                        text: textColor
                    });
                }
            });
        }
    }
    
    /**
     * Улучшенная валидация форм с ARIA
     */
    function initFormValidation() {
        // Обработка отправки форм с novalidate
        document.addEventListener('submit', function(e) {
            const form = e.target;
            if (form.hasAttribute('novalidate')) {
                e.preventDefault();
                validateForm(form);
            }
        });
        
        // Валидация в реальном времени
        document.addEventListener('blur', function(e) {
            if (e.target.matches('input, select, textarea')) {
                validateField(e.target);
            }
        }, true);
        
        // Очистка ошибок при вводе
        document.addEventListener('input', function(e) {
            if (e.target.matches('input, select, textarea')) {
                clearFieldValidation(e.target);
            }
        });
    }
    
    function validateForm(form) {
        const fields = form.querySelectorAll('input[required], select[required], textarea[required]');
        let isValid = true;
        let firstInvalidField = null;
        
        fields.forEach(field => {
            if (!validateField(field) && !firstInvalidField) {
                firstInvalidField = field;
                isValid = false;
            }
        });
        
        if (!isValid && firstInvalidField) {
            firstInvalidField.focus();
            announceFormErrors(form);
        } else {
            submitForm(form);
        }
    }
    
    function validateField(field) {
        const isValid = field.checkValidity();
        const feedback = field.parentNode.querySelector('.invalid-feedback');
        
        field.setAttribute('aria-invalid', !isValid);
        field.classList.toggle('is-invalid', !isValid);
        field.classList.toggle('is-valid', isValid && field.value);
        
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
    
    function clearFieldValidation(field) {
        field.setAttribute('aria-invalid', 'false');
        field.classList.remove('is-invalid', 'is-valid');
        
        const feedback = field.parentNode.querySelector('.invalid-feedback');
        if (feedback) {
            feedback.style.display = 'none';
        }
    }
    
    function getValidationMessage(field) {
        if (field.validity.valueMissing) {
            const label = field.previousElementSibling;
            const fieldName = label ? label.textContent.replace('*', '').trim() : 'Поле';
            return `${fieldName} обязательно для заполнения`;
        }
        if (field.validity.typeMismatch) {
            return 'Неверный формат данных';
        }
        if (field.validity.rangeUnderflow) {
            return `Значение должно быть не менее ${field.min}`;
        }
        if (field.validity.rangeOverflow) {
            return `Значение должно быть не более ${field.max}`;
        }
        if (field.validity.tooLong) {
            return `Слишком длинный текст (максимум ${field.maxLength} символов)`;
        }
        return field.validationMessage || 'Неверное значение';
    }
    
    function announceFormErrors(form) {
        const invalidFields = form.querySelectorAll('.is-invalid');
        const message = `Форма содержит ${invalidFields.length} ошибок. Исправьте поля и попробуйте снова.`;
        
        const announcer = document.getElementById('aria-live-assertive') || createAnnouncer();
        announcer.announce(message);
    }
    
    function submitForm(form) {
        // Показать индикатор загрузки
        const loadingIndicator = form.querySelector('#form-loading');
        const submitButton = form.querySelector('button[type="submit"]');
        
        if (loadingIndicator) {
            loadingIndicator.style.display = 'block';
        }
        
        if (submitButton) {
            submitButton.disabled = true;
            submitButton.setAttribute('aria-busy', 'true');
        }
        
        // Отправить форму
        form.submit();
    }
    
    /**
     * Поддержка skip links
     */
    function initSkipLinks() {
        document.addEventListener('click', function(e) {
            if (e.target.matches('.skip-link')) {
                e.preventDefault();
                const targetId = e.target.getAttribute('href').substring(1);
                const target = document.getElementById(targetId);
                
                if (target) {
                    target.tabIndex = -1;
                    target.focus();
                    target.addEventListener('blur', function() {
                        target.removeAttribute('tabindex');
                    }, { once: true });
                }
            }
        });
    }
    
    // Запустить проверки в dev режиме
    setTimeout(logA11yIssues, 1000);
    
})();