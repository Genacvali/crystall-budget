// Expenses page entry point
import * as ui from '../modules/ui.js';
import { initForms } from '../modules/forms.js';
import { initSwipeCards } from '../modules/swipe.js';

document.addEventListener('DOMContentLoaded', () => {
  // Initialize UI components
  ui.initOfflineBadge();
  ui.initThemeToggle();
  ui.initSidebar();
  ui.initTooltips();

  // Initialize modals
  if (window.ModalManager) {
    window.ModalManager.init();
  }

  // Initialize forms
  initForms();

  // Initialize swipe cards for mobile
  initSwipeCards();

  // Auto-flush outbox on page load
  if (window.CBOffline) {
    window.CBOffline.flushOutbox();
  }

  // Date filter navigation
  const dateFilter = document.getElementById('expenseDateFilter');
  if (dateFilter) {
    dateFilter.addEventListener('change', function() {
      const selectedDate = this.value; // YYYY-MM-DD format
      if (selectedDate) {
        // Extract year-month from date
        const yearMonth = selectedDate.slice(0, 7);
        const url = new URL(window.location);
        url.searchParams.set('ym', yearMonth);
        // Force reload to prevent caching
        window.location.replace(url.toString());
      }
    });
  }

  // Auto-focus amount input after category selection
  const categorySelect = document.getElementById('category_id');
  const amountInput = document.getElementById('amount');
  if (categorySelect && amountInput) {
    categorySelect.addEventListener('change', function() {
      if (this.value) {
        setTimeout(() => amountInput.focus(), 100);
      }
    });
  }
  
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