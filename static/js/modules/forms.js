// Form handling for modals
import { postExpense, postIncome } from './api.js';
import { showToast } from './ui.js';

export function initForms() {
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