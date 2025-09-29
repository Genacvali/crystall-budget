// Goals page entry point
import * as ui from '../modules/ui.js';
import { initForms } from '../modules/forms.js';
import { initSwipeCards } from '../modules/swipe.js';

document.addEventListener('DOMContentLoaded', () => {
  // Initialize UI components
  ui.initOfflineBadge();
  ui.initThemeToggle();
  ui.initSidebar();
  ui.initTooltips();
  
  // Initialize forms
  initForms();
  
  // Initialize swipe cards for mobile
  initSwipeCards();
  
  // Auto-flush outbox on page load
  if (window.CBOffline) {
    window.CBOffline.flushOutbox();
  }
  
  // Goals-specific logic
  initGoalsPageLogic();
  
  // Initialize confirm delete buttons
  document.querySelectorAll('[data-confirm-delete]').forEach(btn => {
    btn.addEventListener('click', function(e) {
      e.preventDefault();
      const confirmText = this.getAttribute('data-confirm-delete');
      
      if (window.ModalManager) {
        window.ModalManager.confirm({
          title: 'Подтверждение удаления',
          message: confirmText,
          confirmText: 'Удалить',
          cancelText: 'Отмена',
          confirmClass: 'btn-danger'
        }).then(() => {
          // User confirmed, submit the form
          const form = this.closest('form');
          if (form) {
            form.submit();
          }
        });
      } else {
        // Fallback to native confirm
        if (confirm(confirmText)) {
          const form = this.closest('form');
          if (form) {
            form.submit();
          }
        }
      }
    });
  });
});

function initGoalsPageLogic() {
  // Любая специфическая логика для страницы целей
  // Например, анимации прогресс-баров, автофокус и т.д.
  
  // Initialize Bootstrap dropdowns
  const dropdownTriggers = document.querySelectorAll('[data-bs-toggle="dropdown"]');
  dropdownTriggers.forEach(trigger => {
    if (window.bootstrap) {
      new bootstrap.Dropdown(trigger);
    }
  });
}