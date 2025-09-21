// API helpers using CBOffline
export async function postExpense(payload) {
  return window.CBOffline.apiSend('POST', '/api/expenses', payload);
}

export async function postIncome(payload) {
  return window.CBOffline.apiSend('POST', '/api/income', payload);
}

export async function updateExpense(id, payload) {
  return window.CBOffline.apiSend('PUT', `/api/expenses/${id}`, payload);
}

export async function deleteExpense(id) {
  return window.CBOffline.apiSend('DELETE', `/api/expenses/${id}`);
}