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
  
  // Initialize forms
  initForms();
  
  // Initialize swipe cards for mobile
  initSwipeCards();
  
  // Auto-flush outbox on page load
  if (window.CBOffline) {
    window.CBOffline.flushOutbox();
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
      const confirmText = this.getAttribute('data-confirm-delete');
      if (!confirm(confirmText)) {
        e.preventDefault();
        return false;
      }
    });
  });
});