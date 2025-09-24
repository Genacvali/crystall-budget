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
      const payload = {
        operationId: Date.now() + '-' + Math.random().toString(36),
        amount: Number(form.amount.value),
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
    });
  })();

  // Income form submit
  (function setupIncomeForm() {
    const form = document.getElementById('incomeForm');
    if (!form) return;

    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const payload = {
        operationId: Date.now() + '-' + Math.random().toString(36),
        amount: Number(form.amount.value),
        source_id: form.source_id.value,
        date: form.date.value
      };

      try {
        const response = await fetch('/api/v1/income', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });

        if (response.ok) {
          notify('Доход успешно добавлен', 'success');

          // Close modal
          const modal = getModalInstance('incomeModal');
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

      if (typeof window.confirmDelete === 'function') {
        window.confirmDelete(
          'Удалить эту категорию? Все связанные расходы также будут удалены.',
          async () => {
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
        );
      } else {
        // Fallback confirm
        if (confirm('Удалить категорию?')) {
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

})();