/* Dashboard page entry script: extracted from templates/pages/dashboard.html inline JS */
(function () {
  'use strict';

  // Utilities
  function getModalInstance(id) {
    const el = document.getElementById(id);
    return el ? (bootstrap.Modal.getInstance(el) || new bootstrap.Modal(el)) : null;
  }

  function todayISO() {
    try {
      return new Date().toISOString().slice(0, 10);
    } catch (e) {
      const d = new Date();
      const m = String(d.getMonth() + 1).padStart(2, '0');
      const day = String(d.getDate()).padStart(2, '0');
      return `${d.getFullYear()}-${m}-${day}`;
    }
  }

  function safeResetDate(inputEl) {
    if (!inputEl) return;
    const original = inputEl.getAttribute('value');
    inputEl.value = original || todayISO();
  }

  // Global toast from static/js/app.js. Provide minimal fallback if missing.
  function notify(msg, type) {
    if (typeof window.showToast === 'function') {
      window.showToast(msg, type);
    } else {
      // fallback
      (type === 'danger' ? console.error : console.log)(msg);
    }
  }

  // Expense form submit
  (function setupExpenseForm() {
    const form = document.getElementById('expenseForm');
    if (!form) return;

    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      
      const multiCategoryCheckbox = document.getElementById('multiCategory');
      const isMultiCategory = multiCategoryCheckbox && multiCategoryCheckbox.checked;
      
      if (isMultiCategory) {
        // Multi-category mode
        const selectedCategories = [];
        const totalAmount = parseFloat(form.amount.value.replace(',', '.')) || 0;
        let usedAmount = 0;
        
        // Collect selected categories and amounts
        document.querySelectorAll('.category-checkbox:checked').forEach(checkbox => {
          const categoryId = checkbox.value;
          const amountInput = document.getElementById('amount_' + categoryId);
          const amount = parseFloat(amountInput.value.replace(',', '.')) || 0;
          
          if (amount > 0) {
            selectedCategories.push({
              category_id: categoryId,
              amount: amount
            });
            usedAmount += amount;
          }
        });
        
        // Validate
        if (selectedCategories.length === 0) {
          notify('Выберите хотя бы одну категорию и укажите сумму', 'danger');
          return;
        }
        
        if (Math.abs(usedAmount - totalAmount) > 0.01) {
          notify('Сумма по категориям должна равняться общей сумме', 'danger');
          return;
        }
        
        // Send multiple expense requests
        try {
          const promises = selectedCategories.map(item => {
            const payload = {
              operationId: Date.now() + '-' + Math.random().toString(36) + '-' + item.category_id,
              amount: item.amount,
              category_id: item.category_id,
              date: form.date.value,
              note: form.note.value
            };
            
            return fetch('/api/v1/expenses', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify(payload)
            });
          });
          
          const responses = await Promise.all(promises);
          
          // Check if all requests succeeded
          const failed = responses.filter(r => !r.ok);
          if (failed.length > 0) {
            throw new Error(`${failed.length} из ${responses.length} расходов не удалось сохранить`);
          }
          
          notify(`Добавлено ${selectedCategories.length} расходов`, 'success');
          
          // Close modal and reset
          const modal = getModalInstance('expenseModal');
          modal?.hide();
          form.reset();
          const multiCategoryCheckbox = document.getElementById('multiCategory');
          if (multiCategoryCheckbox) {
            multiCategoryCheckbox.checked = false;
            // Trigger change event to reset UI
            multiCategoryCheckbox.dispatchEvent(new Event('change'));
          }
          safeResetDate(form.querySelector('input[name="date"]'));
          
          setTimeout(() => location.reload(), 1000);
          
        } catch (error) {
          console.error('Error adding multi-category expense:', error);
          notify('Ошибка при добавлении расходов: ' + error.message, 'danger');
        }
        
      } else {
        // Single category mode (original logic)
        const payload = {
          operationId: Date.now() + '-' + Math.random().toString(36),
          amount: Number(form.amount.value.replace(',', '.')),
          category_id: form.category_id.value,
          date: form.date.value,
          note: form.note.value
        };

        try {
          const response = await fetch('/api/v1/expenses', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
          });

          if (response.ok) {
            notify('Расход успешно добавлен', 'success');

            // Close modal
            const modal = getModalInstance('expenseModal');
            modal?.hide();

            // Reset form
            form.reset();
            safeResetDate(form.querySelector('input[name="date"]'));

            // Refresh page
            setTimeout(() => location.reload(), 1000);
          } else {
            throw new Error('Ошибка сервера');
          }
        } catch (error) {
          console.error('Error adding expense:', error);
          notify('Ошибка при добавлении расхода', 'danger');
        }
      }
    });
  })();

  // Income form submit
  (function setupIncomeForm() {
    const form = document.getElementById('incomeForm');
    if (!form) return;

    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      
      // Create form data for regular POST request
      const formData = new FormData();
      formData.append('source_name', form.source_name.value);
      formData.append('amount', form.amount.value);
      formData.append('date', form.date.value);
      
      // Add CSRF token
      const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
      if (csrfToken) {
        formData.append('csrf_token', csrfToken);
      }

      try {
        const response = await fetch('/income', {
          method: 'POST',
          body: formData
        });

        if (response.ok) {
          notify('Доход успешно добавлен', 'success');

          // Close modal
          const modal = getModalInstance('incomeModal');
          modal?.hide();

          // Reset form
          form.reset();
          safeResetDate(form.querySelector('input[name="date"]'));
          
          // Clear validation states
          form.classList.remove('was-validated');
          form.querySelectorAll('.is-invalid, .is-valid').forEach(el => {
            el.classList.remove('is-invalid', 'is-valid');
          });

          // Refresh page
          setTimeout(() => location.reload(), 1000);
        } else {
          throw new Error('Ошибка сервера');
        }
      } catch (error) {
        console.error('Error adding income:', error);
        notify('Ошибка при добавлении дохода', 'danger');
      }
    });
  })();

  /* Category edit handler: open modal, patch, update DOM */
(function setupCategoryEdit() {
  const list = document.getElementById('catList');
  const modalEl = document.getElementById('categoryModal');
  const form = document.getElementById('categoryForm');
  if (!list || !modalEl || !form) return;

  const modal = getModalInstance('categoryModal');

  // Open modal on edit click
  document.addEventListener('click', (e) => {
    const btn = e.target.closest('[data-action="edit"][data-id]');
    if (!btn) return;

    const id = btn.dataset.id;
    // Card may be the closest article with class 'cat'
    const card =
      list.querySelector(`article.cat [data-id="${id}"]`)?.closest('article.cat') ||
      btn.closest('article.cat');

    if (!card) return;

    // Populate fields from data-attributes
    const idEl = document.getElementById('catId');
    const nameEl = document.getElementById('catName');
    const typeEl = document.getElementById('catLimitType');
    const valueEl = document.getElementById('catValue');

    if (idEl) idEl.value = id || '';
    if (nameEl) nameEl.value = card.dataset.name || '';
    if (typeEl) typeEl.value = card.dataset.limitType || 'fixed';
    if (valueEl) valueEl.value = String(Number(card.dataset.limit || 0));

    modal?.show();
  });

  // Save category
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const fd = new FormData(form);
    const id = Number(fd.get('id'));
    const payload = {
      name: String(fd.get('name') || '').trim(),
      limit_type: String(fd.get('limit_type') || 'fixed'),
      value: Number(fd.get('value') || 0)
    };

    if (!id || !payload.name) {
      notify('Заполните корректные данные категории', 'danger');
      return;
    }

    try {
      const response = await fetch(`/api/v1/categories/${id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (!response.ok) throw new Error('HTTP ' + response.status);

      notify('Категория обновлена', 'success');

      // Update DOM
      const card =
        list.querySelector(`article.cat [data-id="${id}"]`)?.closest('article.cat') ||
        list.querySelector(`article.cat[data-id="${id}"]`);

      if (card) {
        card.dataset.name = payload.name;
        card.dataset.limit = String(payload.value);
        card.dataset.limitType = payload.limit_type;

        const titleEl = card.querySelector('.cat-title');
        if (titleEl) titleEl.textContent = payload.name;

        const metaEl = card.querySelector('.cat-meta');
        if (metaEl) {
          metaEl.textContent =
            payload.limit_type === 'percent'
              ? `Процент ${isFinite(payload.value) ? payload.value.toFixed(2) : payload.value}%`
              : `Фикс ${isFinite(payload.value) ? payload.value.toFixed(2) : payload.value} ₽`;
        }

        const limitSpan = card.querySelector('.cat-right .muted.mono');
        if (limitSpan) {
          limitSpan.textContent = isFinite(payload.value) ? payload.value.toFixed(2) + ' ₽' : String(payload.value) + ' ₽';
        }
      }

      modal?.hide();
    } catch (err) {
      console.error(err);
      notify('Ошибка при сохранении категории', 'danger');
    }
  });
})();

// Category deletion handler (uses global confirm modal)
  (function setupCategoryDelete() {
    document.addEventListener('click', async function (e) {
      const trigger = e.target.closest('[data-action="delete"][data-id]');
      if (!trigger) return;

      const catId = trigger.dataset.id;
      if (!catId) return;

      // Use unified modal system for confirmation
      if (window.ModalManager) {
        window.ModalManager.confirm({
          title: 'Удаление категории',
          message: 'Удалить эту категорию? Все связанные расходы также будут удалены.',
          confirmText: 'Удалить',
          cancelText: 'Отмена',
          confirmClass: 'btn-danger'
        }).then(async () => {
          try {
            const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');
            const response = await fetch(`/categories/delete/${catId}`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
              body: `csrf_token=${encodeURIComponent(csrfToken)}`
            });
            if (response.ok) {
              notify('Категория успешно удалена', 'success');
              setTimeout(() => location.reload(), 1000);
            } else {
              throw new Error('Ошибка сервера');
            }
          } catch (err) {
            console.error(err);
            notify('Ошибка при удалении категории', 'danger');
          }
        }).catch(() => {
          // User cancelled - no action needed
        });
      } else {
        // Fallback to native confirm
        if (confirm('Удалить категорию? Все связанные расходы также будут удалены.')) {
          try {
            const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');
            const response = await fetch(`/categories/delete/${catId}`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
              body: `csrf_token=${encodeURIComponent(csrfToken)}`
            });
            if (response.ok) {
              notify('Категория успешно удалена', 'success');
              setTimeout(() => location.reload(), 1000);
            } else {
              throw new Error('Ошибка сервера');
            }
          } catch (err) {
            console.error(err);
            notify('Ошибка при удалении категории', 'danger');
          }
        }
      }
    });
  })();

  // Amount field input filtering for dashboard income modal
  const dashboardAmountField = document.getElementById('incAmount');
  if (dashboardAmountField) {
    // Filter input - allow only digits, comma, dot
    dashboardAmountField.addEventListener('input', function(e) {
      let value = e.target.value;
      
      // Remove any characters that aren't digits, comma, or dot
      value = value.replace(/[^0-9,\.]/g, '');
      
      // Allow only one decimal separator
      const commaCount = (value.match(/,/g) || []).length;
      const dotCount = (value.match(/\./g) || []).length;
      
      if (commaCount + dotCount > 1) {
        // Keep only the first separator
        let separatorFound = false;
        value = value.replace(/[,\.]/g, function(match) {
          if (!separatorFound) {
            separatorFound = true;
            return match;
          }
          return '';
        });
      }
      
      // Limit decimal places to 2
      const parts = value.split(/[,\.]/);
      if (parts.length > 1 && parts[1].length > 2) {
        parts[1] = parts[1].substring(0, 2);
        value = parts.join(value.includes(',') ? ',' : '.');
      }
      
      e.target.value = value;
    });
    
    // Normalize on blur (replace comma with dot)
    dashboardAmountField.addEventListener('blur', function(e) {
      let value = e.target.value.replace(',', '.');
      e.target.value = value;
      
      // Clear invalid state if value is now valid
      if (value.match(/^\d+(\.\d{1,2})?$/)) {
        e.target.classList.remove('is-invalid');
      }
    });
  }

})();

  // Multi-category functionality setup
  (function setupMultiCategory() {
    function toggleMultiCategory() {
      console.log('toggleMultiCategory called');
      const checkbox = document.getElementById('multiCategory');
      const singleGroup = document.getElementById('singleCategoryGroup');
      const multiGroup = document.getElementById('multiCategoryGroup');
      const categoryItems = document.querySelectorAll('.category-item');
      const singleSelect = document.getElementById('expenseCategory');
      
      console.log('Elements found:', {
        checkbox: !!checkbox,
        singleGroup: !!singleGroup,
        multiGroup: !!multiGroup,
        categoryItems: categoryItems.length,
        singleSelect: !!singleSelect
      });
      
      if (!checkbox || !singleGroup || !multiGroup) {
        console.log('Missing required elements, aborting');
        return;
      }
      
      if (checkbox.checked) {
        // Switch to multi-category mode
        singleGroup.style.display = 'none';
        multiGroup.style.display = 'block';
        if (singleSelect) singleSelect.required = false;
        
        // Show all category items
        categoryItems.forEach(item => {
          item.style.display = 'block';
        });
        
        // Update remaining amount
        updateRemainingAmount();
      } else {
        // Switch to single category mode
        singleGroup.style.display = 'block';
        multiGroup.style.display = 'none';
        if (singleSelect) singleSelect.required = true;
        
        // Hide all category items and reset checkboxes
        categoryItems.forEach(item => {
          item.style.display = 'none';
          const checkbox = item.querySelector('.category-checkbox');
          const amountInput = item.querySelector('.category-amount');
          if (checkbox) checkbox.checked = false;
          if (amountInput) {
            amountInput.disabled = true;
            amountInput.value = '';
          }
        });
      }
    }

    function toggleCategoryAmount(checkbox, categoryId) {
      const amountInput = document.getElementById('amount_' + categoryId);
      if (amountInput) {
        amountInput.disabled = !checkbox.checked;
        if (!checkbox.checked) {
          amountInput.value = '';
        }
        updateRemainingAmount();
      }
    }

    function updateRemainingAmount() {
      const totalAmountInput = document.getElementById('expenseAmount');
      const remainingSpan = document.getElementById('remainingAmount');
      
      if (!totalAmountInput || !remainingSpan) return;
      
      const totalAmount = parseFloat(totalAmountInput.value.replace(',', '.')) || 0;
      let usedAmount = 0;
      
      // Sum all category amounts
      document.querySelectorAll('.category-amount:not([disabled])').forEach(input => {
        const amount = parseFloat(input.value.replace(',', '.')) || 0;
        usedAmount += amount;
      });
      
      const remaining = totalAmount - usedAmount;
      remainingSpan.textContent = remaining.toFixed(2);
      
      // Color coding
      if (remaining < 0) {
        remainingSpan.style.color = 'red';
      } else if (remaining === 0) {
        remainingSpan.style.color = 'green';
      } else {
        remainingSpan.style.color = '';
      }
    }

    // Initialize event listeners with multiple fallbacks
    function initializeMultiCategory() {
      console.log('initializeMultiCategory called');
      const multiCategoryCheckbox = document.getElementById('multiCategory');
      console.log('multiCategoryCheckbox found:', !!multiCategoryCheckbox);
      
      if (multiCategoryCheckbox && !multiCategoryCheckbox.hasAttribute('data-initialized')) {
        console.log('Adding change listener to multiCategory checkbox');
        multiCategoryCheckbox.addEventListener('change', toggleMultiCategory);
        multiCategoryCheckbox.setAttribute('data-initialized', 'true');
      } else if (multiCategoryCheckbox) {
        console.log('multiCategory checkbox already initialized');
      }
      
      const totalAmountInput = document.getElementById('expenseAmount');
      if (totalAmountInput && !totalAmountInput.hasAttribute('data-initialized')) {
        totalAmountInput.addEventListener('input', updateRemainingAmount);
        totalAmountInput.setAttribute('data-initialized', 'true');
      }
      
      // Add event listeners to category checkboxes and amount inputs
      document.querySelectorAll('.category-checkbox:not([data-initialized])').forEach(checkbox => {
        checkbox.addEventListener('change', function() {
          const categoryId = this.getAttribute('data-category-id') || this.value;
          toggleCategoryAmount(this, categoryId);
        });
        checkbox.setAttribute('data-initialized', 'true');
      });
      
      document.querySelectorAll('.category-amount:not([data-initialized])').forEach(input => {
        input.addEventListener('input', updateRemainingAmount);
        input.setAttribute('data-initialized', 'true');
      });
    }

    // Try multiple initialization points
    document.addEventListener('DOMContentLoaded', initializeMultiCategory);
    
    // If already loaded
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', initializeMultiCategory);
    } else {
      initializeMultiCategory();
    }

    // Also listen for modal shown event to re-initialize
    function setupModalListener() {
      const expenseModal = document.getElementById('expenseModal');
      if (expenseModal && !expenseModal.hasAttribute('data-listener-added')) {
        expenseModal.addEventListener('shown.bs.modal', function() {
          console.log('Modal shown, initializing multi-category functionality');
          initializeMultiCategory();
        });
        expenseModal.setAttribute('data-listener-added', 'true');
      }
    }
    
    // Try to set up modal listener immediately and after DOM load
    setupModalListener();
    document.addEventListener('DOMContentLoaded', setupModalListener);
  })();