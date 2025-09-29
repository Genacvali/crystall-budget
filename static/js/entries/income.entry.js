// Income page entry point
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
  
  // Income-specific logic
  initIncomePageLogic();
  
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
          cancelText: 'Отмена'
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

function initIncomePageLogic() {
  // Если дата не задана — подставляем сегодня
  const dateInput = document.getElementById('date');
  if (dateInput && !dateInput.value) {
    const now = new Date();
    dateInput.value = now.toISOString().slice(0, 10);
  }

  // После выбора источника — фокус в "Сумма"
  const source = document.getElementById('source_id');
  const amount = document.getElementById('amount');
  if (source && amount) {
    source.addEventListener('change', () => setTimeout(() => amount.focus(), 60));
  }

  // Нормализация суммы до двух знаков на blur
  if (amount) {
    amount.addEventListener('blur', () => {
      const v = parseFloat(amount.value);
      if (!isNaN(v) && v > 0) amount.value = v.toFixed(2);
    });
  }
  
  // Focus management for form fields
  const sourceNameInput = document.getElementById('source_name');
  const amountInput = document.getElementById('amount');
  if (sourceNameInput && amountInput) {
    sourceNameInput.addEventListener('change', function() {
      if (this.value.trim()) {
        setTimeout(() => amountInput.focus(), 100);
      }
    });
  }
}