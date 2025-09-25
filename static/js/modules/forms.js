// Form handling for modals
import { postExpense, postIncome } from './api.js';
import { showToast } from './ui.js';

export function initForms() {
  // Initialize dirty field tracking for income modal
  initIncomeModalValidation();
  
  // Handle expense form
  document.addEventListener('submit', async (e) => {
    if (e.target.matches('[data-form="expense"]')) {
      e.preventDefault();
      await handleExpenseForm(e.target);
    }
    
    if (e.target.matches('[data-form="income"]')) {
      e.preventDefault();
      await handleIncomeForm(e.target);
    }
  });
}

function initIncomeModalValidation() {
  const modal = document.getElementById('incomeModal');
  if (!modal) return;

  const form = modal.querySelector('#incomeForm');
  const amount = form?.querySelector('#incAmount');

  if (!form) return;

  // Убираем любые классы валидации при открытии модала
  modal.addEventListener('show.bs.modal', () => {
    form.classList.remove('was-validated');
    form.querySelectorAll('.form-control, .form-select').forEach(el => {
      el.classList.remove('dirty', 'is-valid', 'is-invalid');
    });
  });

  // помечаем поля как "dirty" только после реального взаимодействия
  form.querySelectorAll('input, select').forEach(el => {
    let hasBeenTouched = false;
    
    el.addEventListener('focus', () => {
      hasBeenTouched = true;
    });
    
    el.addEventListener('input', () => {
      if (hasBeenTouched) {
        el.classList.add('dirty');
      }
    });
    
    el.addEventListener('blur', () => {
      if (hasBeenTouched) {
        el.classList.add('dirty');
      }
    });
  });

  form.addEventListener('submit', (e) => {
    // помечаем все поля как dirty при попытке сабмита
    form.querySelectorAll('input, select').forEach(el => {
      el.classList.add('dirty');
    });

    // нормализуем сумму "1 000,5" -> "1000.50"
    if (amount && amount.value) {
      const v = amount.value.replace(/\s+/g, '').replace(',', '.');
      if (/^\d+(\.\d{1,2})?$/.test(v)) {
        amount.value = (Math.round(parseFloat(v) * 100) / 100).toFixed(2);
      }
    }
    
    if (!form.checkValidity()) {
      e.preventDefault();
      e.stopPropagation();
      form.classList.add('was-validated'); // активируем показ ошибок
      return false; // Don't proceed with form submission
    }
  });
}

async function handleExpenseForm(form) {
  const formData = new FormData(form);
  const payload = {
    amount: Number(formData.get('amount')),
    category_id: formData.get('category_id'),
    date: formData.get('date'),
    note: formData.get('note')
  };
  
  try {
    const res = await postExpense(payload);
    if (res.queued) {
      showToast('Расход сохранен (офлайн, будет отправлен при восстановлении сети)', 'warning');
    } else {
      showToast('Расход успешно добавлен', 'success');
    }
    
    // Close modal
    const modal = bootstrap.Modal.getInstance(document.getElementById('expenseModal'));
    if (modal) modal.hide();
    
    // Reset form
    form.reset();
    const dateField = form.querySelector('[name="date"]');
    if (dateField) dateField.value = new Date().toISOString().split('T')[0];
    
    // Reload page if online
    if (!res.queued) {
      setTimeout(() => location.reload(), 1000);
    }
  } catch (error) {
    console.error('Error adding expense:', error);
    showToast('Ошибка при добавлении расхода', 'danger');
  }
}

async function handleIncomeForm(form) {
  const formData = new FormData(form);
  const payload = {
    amount: Number(formData.get('amount')),
    source_id: formData.get('source_id'),
    date: formData.get('date')
  };
  
  try {
    const res = await postIncome(payload);
    if (res.queued) {
      showToast('Доход сохранен (офлайн, будет отправлен при восстановлении сети)', 'warning');
    } else {
      showToast('Доход успешно добавлен', 'success');
    }
    
    // Close modal
    const modal = bootstrap.Modal.getInstance(document.getElementById('incomeModal'));
    if (modal) modal.hide();
    
    // Reset form
    form.reset();
    const dateField = form.querySelector('[name="date"]');
    if (dateField) dateField.value = new Date().toISOString().split('T')[0];
    
    // Reload page if online
    if (!res.queued) {
      setTimeout(() => location.reload(), 1000);
    }
  } catch (error) {
    console.error('Error adding income:', error);
    showToast('Ошибка при добавлении дохода', 'danger');
  }
}