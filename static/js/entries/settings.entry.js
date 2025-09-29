// Settings page entry point
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
  
  // Settings-specific logic
  initSettingsPageLogic();
});

function initSettingsPageLogic() {
  // Initialize quick theme toggle in settings page
  const quickThemeToggle = document.getElementById('quickThemeToggle');
  if (quickThemeToggle) {
    quickThemeToggle.addEventListener('change', function() {
      const theme = this.checked ? 'dark' : 'light';
      
      // Update theme immediately for instant feedback
      document.documentElement.setAttribute('data-bs-theme', theme);
      
      // Save to server
      fetch('/set-theme', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': window.getCSRFToken ? window.getCSRFToken() : ''
        },
        body: JSON.stringify({ theme: theme })
      }).catch(error => {
        console.error('Failed to save theme:', error);
        // Revert on error
        document.documentElement.setAttribute('data-bs-theme', this.checked ? 'light' : 'dark');
        this.checked = !this.checked;
      });
    });
  }
  
  // Initialize Bootstrap tooltips for help text
  const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]');
  if (window.bootstrap && tooltipTriggerList.length > 0) {
    [...tooltipTriggerList].map(tooltipTriggerEl => new bootstrap.Tooltip(tooltipTriggerEl));
  }
}