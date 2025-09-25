// Income page entry point
console.log('Income.entry.js file loaded!');

document.addEventListener('DOMContentLoaded', () => {
  console.log('Income.entry.js DOMContentLoaded fired!');
  
  // Initialize income modals
  initIncomeModals();
  
  // Basic tooltip initialization
  const tooltips = document.querySelectorAll('[data-bs-toggle="tooltip"]');
  if (tooltips.length && window.bootstrap) {
    tooltips.forEach(el => new bootstrap.Tooltip(el));
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
});

function initIncomeModals() {
  console.log('initIncomeModals called');
  
  // Edit income modal handling
  const editButtons = document.querySelectorAll('.edit-income-btn');
  const editModal = document.getElementById('editIncomeModal');
  const editForm = document.getElementById('editIncomeForm');
  
  console.log('Found elements:', {
    editButtons: editButtons.length,
    editModal: !!editModal,
    editForm: !!editForm
  });
  
  editButtons.forEach(btn => {
    btn.addEventListener('click', function(e) {
      console.log('Edit button clicked!');
      e.preventDefault();
      e.stopPropagation();
      
      const id = this.dataset.id;
      const source = this.dataset.source;
      const amount = this.dataset.amount;
      const year = this.dataset.year;
      const month = this.dataset.month;
      
      // Fill form fields
      document.getElementById('editIncomeId').value = id;
      document.getElementById('editIncSource').value = source;
      document.getElementById('editIncAmount').value = amount;
      
      // Format month as YYYY-MM for input[type=month]
      const formattedMonth = `${year}-${month.toString().padStart(2, '0')}`;
      document.getElementById('editIncMonth').value = formattedMonth;
      
      // Set form action
      editForm.action = `/budget/income/edit/${id}`;
      
      // Show modal
      const modal = new bootstrap.Modal(editModal);
      modal.show();
    });
  });
  
  // Delete income modal handling
  const deleteButtons = document.querySelectorAll('.delete-income-btn');
  const deleteModal = document.getElementById('deleteIncomeModal');
  const deleteForm = document.getElementById('deleteIncomeForm');
  
  deleteButtons.forEach(btn => {
    btn.addEventListener('click', function(e) {
      console.log('Delete button clicked!');
      e.preventDefault();
      e.stopPropagation();
      
      const id = this.dataset.id;
      const source = this.dataset.source;
      const amount = this.dataset.amount;
      
      // Fill modal content
      document.getElementById('deleteIncomeSource').textContent = source;
      document.getElementById('deleteIncomeAmount').textContent = amount;
      
      // Set form action
      deleteForm.action = `/budget/income/delete/${id}`;
      
      // Show modal
      const modal = new bootstrap.Modal(deleteModal);
      modal.show();
    });
  });
  
  // Handle form submissions
  if (editForm) {
    editForm.addEventListener('submit', function(e) {
      // Normalize amount input
      const amountInput = document.getElementById('editIncAmount');
      if (amountInput && amountInput.value) {
        const v = amountInput.value.replace(',', '.').trim();
        if (/^\d+(\.\d{1,2})?$/.test(v)) {
          amountInput.value = (Math.round(parseFloat(v) * 100) / 100).toFixed(2);
        }
      }
    });
  }
}