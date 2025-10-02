// Expenses page entry point
import * as ui from '../modules/ui.js';
import { initForms } from '../modules/forms.js';
import { initSwipeCards } from '../modules/swipe.js';

console.log('[Expenses] Script file loaded!');

document.addEventListener('DOMContentLoaded', () => {
  console.log('[Expenses] Page loaded, initializing...');
  console.log('[Expenses] Sort buttons:', document.querySelectorAll('.dropdown-menu .dropdown-item').length);
  console.log('[Expenses] Table tbody:', document.querySelector('table tbody'));
  console.log('[Expenses] Expenses list:', document.querySelector('.expenses-list, #expensesList, [data-expenses-container]'));

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

  // Initialize sorting functionality
  console.log('[Expenses] Calling initExpensesSorting...');
  initExpensesSorting();
  console.log('[Expenses] initExpensesSorting called');
});

/**
 * Initialize expenses sorting
 */
function initExpensesSorting() {
  const sortButtons = document.querySelectorAll('.dropdown-menu .dropdown-item');
  const sortToggleBtn = document.querySelector('[data-bs-toggle="dropdown"]');
  const expensesList = document.querySelector('.expenses-list, #expensesList, [data-expenses-container]');

  if (!sortButtons.length) {
    console.warn('[Expenses] No sort buttons found');
    return;
  }

  // Try to find expenses container
  let container = expensesList;
  if (!container) {
    // Try to find table tbody
    const tbody = document.querySelector('table tbody');
    if (tbody) {
      container = tbody;
    }
  }
  if (!container) {
    // Fallback: find by common expense card classes
    const cards = document.querySelectorAll('.expense-card, [data-expense-id]');
    if (cards.length) {
      container = cards[0].parentElement;
    }
  }

  if (!container) {
    console.warn('[Expenses] No expenses container found');
    return;
  }

  console.log('[Expenses] Sorting initialized, container:', container, 'items:', container.children.length);

  sortButtons.forEach(btn => {
    btn.addEventListener('click', function() {
      const sortType = this.textContent.trim();
      console.log('[Expenses] Sorting by:', sortType);

      // Update button text
      if (sortToggleBtn) {
        const icon = sortToggleBtn.querySelector('i.bi-sort-down, i.bi-sort-up');
        const caretIcon = sortToggleBtn.querySelector('i.bi-caret-down-fill');
        const textSpan = sortToggleBtn.querySelector('span');
        if (textSpan) {
          const iconHTML = icon ? icon.outerHTML : '<i class="bi bi-sort-down me-2"></i>';
          textSpan.innerHTML = `${iconHTML}${sortType}`;
        }
      }

      // Get all expense items
      const items = Array.from(container.children);

      // Sort items
      items.sort((a, b) => {
        if (sortType.includes('дате')) {
          const dateA = getExpenseDate(a);
          const dateB = getExpenseDate(b);
          return sortType.includes('новые') ? dateB - dateA : dateA - dateB;
        } else if (sortType.includes('сумме')) {
          const amountA = getExpenseAmount(a);
          const amountB = getExpenseAmount(b);
          return sortType.includes('убыв') ? amountB - amountA : amountA - amountB;
        } else if (sortType.includes('категории')) {
          const catA = getExpenseCategory(a);
          const catB = getExpenseCategory(b);
          return catA.localeCompare(catB, 'ru');
        }
        return 0;
      });

      // Re-append items in sorted order
      items.forEach(item => container.appendChild(item));

      console.log('[Expenses] Sorted successfully');
    });
  });
}

/**
 * Get expense date from card
 */
function getExpenseDate(card) {
  // Try data attribute first
  const dateAttr = card.getAttribute('data-expense-date') || card.getAttribute('data-date');
  if (dateAttr) {
    return new Date(dateAttr);
  }

  // Try to find date in card content
  const dateText = card.querySelector('.expense-date, [data-date-text], .text-muted')?.textContent;
  if (dateText) {
    // Parse Russian date format (e.g., "15 янв 2024")
    const match = dateText.match(/(\d{1,2})\s+(\S+)\s+(\d{4})/);
    if (match) {
      const months = ['янв', 'фев', 'мар', 'апр', 'мая', 'июн', 'июл', 'авг', 'сен', 'окт', 'ноя', 'дек'];
      const day = parseInt(match[1]);
      const monthIndex = months.findIndex(m => match[2].toLowerCase().includes(m));
      const year = parseInt(match[3]);
      if (monthIndex >= 0) {
        return new Date(year, monthIndex, day);
      }
    }
  }

  return new Date(0); // Default to epoch if date not found
}

/**
 * Get expense amount from card
 */
function getExpenseAmount(card) {
  // Try data attribute first
  const amountAttr = card.getAttribute('data-expense-amount') || card.getAttribute('data-amount');
  if (amountAttr) {
    return parseFloat(amountAttr);
  }

  // Try to find amount in card content
  const amountText = card.querySelector('.expense-amount, [data-amount-text], strong')?.textContent;
  if (amountText) {
    // Remove currency symbols and spaces, replace comma with dot
    const cleaned = amountText.replace(/[^\d,.-]/g, '').replace(/\s/g, '').replace(',', '.');
    const amount = parseFloat(cleaned);
    if (!isNaN(amount)) {
      return amount;
    }
  }

  return 0; // Default to 0 if amount not found
}

/**
 * Get expense category from card
 */
function getExpenseCategory(card) {
  // Try data attribute first
  const catAttr = card.getAttribute('data-expense-category') || card.getAttribute('data-category');
  if (catAttr) {
    return catAttr;
  }

  // Try to find category in card content
  const catText = card.querySelector('.expense-category, [data-category-text], .badge')?.textContent;
  return catText ? catText.trim() : '';
}