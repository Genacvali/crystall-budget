// API utility functions

export async function postExpense(data) {
  const formData = new FormData();
  Object.entries(data).forEach(([key, value]) => {
    formData.append(key, value);
  });

  const response = await fetch('/budget/expenses/add', {
    method: 'POST',
    body: formData,
    headers: {
      'X-Requested-With': 'XMLHttpRequest'
    }
  });

  return response;
}

export async function postIncome(data) {
  const formData = new FormData();
  Object.entries(data).forEach(([key, value]) => {
    formData.append(key, value);
  });

  const response = await fetch('/budget/income/add', {
    method: 'POST',
    body: formData,
    headers: {
      'X-Requested-With': 'XMLHttpRequest'
    }
  });

  return response;
}

export async function deleteExpense(expenseId) {
  const response = await fetch(`/budget/expenses/${expenseId}/delete`, {
    method: 'POST',
    headers: {
      'X-Requested-With': 'XMLHttpRequest'
    }
  });

  return response;
}

export async function deleteIncome(incomeId) {
  const response = await fetch(`/budget/income/${incomeId}/delete`, {
    method: 'POST',
    headers: {
      'X-Requested-With': 'XMLHttpRequest'
    }
  });

  return response;
}
