// Dashboard page entry point
import * as ui from '../modules/ui.js';
import { initForms } from '../modules/forms.js';

document.addEventListener('DOMContentLoaded', () => {
  // Initialize UI components
  ui.initOfflineBadge();
  ui.initThemeToggle();
  ui.initSidebar();
  ui.initTooltips();
  
  // Initialize forms
  initForms();
  
  // Auto-flush outbox on page load
  if (window.CBOffline) {
    window.CBOffline.flushOutbox();
  }
  
  // Category actions (edit/delete)
  document.addEventListener('click', (e) => {
    const button = e.target.closest('[data-action]');
    
    if (button) {
      const action = button.dataset.action;
      const id = button.dataset.id;
      
      if (action === 'edit') {
        // Переход на страницу редактирования категории
        window.location.href = `/categories`;
      }
      
      if (action === 'delete') {
        if (confirm('Удалить категорию? Это действие необратимо.')) {
          fetch(`/categories/delete/${id}`, {method:'POST'})
            .then(response => {
              if (response.ok) {
                location.reload();
              } else {
                alert('Ошибка при удалении категории');
              }
            })
            .catch(error => {
              console.error('Error:', error);
              alert('Ошибка при удалении категории');
            });
        }
      }
    }
  });
});