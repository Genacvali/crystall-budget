// UI utilities
import { qs, on } from './dom.js';

// Toast functionality
export function showToast(message, type = 'info') {
  const container = qs('#toastContainer');
  if (!container) return;
  
  const id = 'toast-' + Date.now();
  container.insertAdjacentHTML('afterbegin', `
    <div id="${id}" class="toast" role="alert" data-bs-autohide="true" data-bs-delay="5000">
      <div class="toast-header">
        <i class="bi bi-${type === 'danger' ? 'exclamation-triangle' : type === 'success' ? 'check-circle' : 'info-circle'} text-${type} me-2"></i>
        <strong class="me-auto">CrystalBudget</strong>
        <button type="button" class="btn-close" data-bs-dismiss="toast"></button>
      </div>
      <div class="toast-body">${message}</div>
    </div>
  `);
  
  const el = qs('#' + id);
  if (typeof bootstrap !== 'undefined') {
    new bootstrap.Toast(el).show();
  } else {
    el.style.display = 'block';
    setTimeout(() => el.remove(), 5000);
  }
}

// Offline indicator
export function initOfflineBadge() {
  function updateOfflineIndicator() {
    const indicator = qs('#offlineIndicator');
    if (indicator) {
      indicator.style.display = navigator.onLine ? 'none' : 'flex';
    }
  }
  
  updateOfflineIndicator();
  window.addEventListener('online', updateOfflineIndicator);
  window.addEventListener('offline', updateOfflineIndicator);
}

// Theme toggle
export function initThemeToggle() {
  function updateThemeToggle(theme) {
    // Theme toggle logic
    const lightIcon = qs('#light-icon');
    const darkIcon = qs('#dark-icon');
    const themeSwitch = qs('#theme-switch');
    
    if (lightIcon && darkIcon && themeSwitch) {
      if (theme === 'dark') {
        lightIcon.style.opacity = '0.3';
        darkIcon.style.opacity = '1';
        themeSwitch.style.transform = 'translateX(20px)';
      } else {
        lightIcon.style.opacity = '1';
        darkIcon.style.opacity = '0.3';
        themeSwitch.style.transform = 'translateX(0)';
      }
    }
  }

  function toggleTheme() {
    const current = document.documentElement.getAttribute('data-bs-theme') || 'light';
    const newTheme = current === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-bs-theme', newTheme);
    localStorage.setItem('theme', newTheme);
    updateThemeToggle(newTheme);
    
    const meta = qs('meta[name="theme-color"]');
    if (meta) meta.content = newTheme === 'dark' ? '#212529' : '#4fb3d9';
  }

  // Initialize
  const theme = document.documentElement.getAttribute('data-bs-theme') || 'light';
  updateThemeToggle(theme);
  
  // Event delegation for theme toggles
  document.addEventListener('click', (e) => {
    if (e.target.closest('[data-action="toggle-theme"]')) {
      e.preventDefault();
      toggleTheme();
    }
  });
}

// Sidebar toggle
export function initSidebar() {
  function toggleSidebar() {
    const sidebar = qs('#sidebar');
    const overlay = qs('#sidebarOverlay');
    if (sidebar && overlay) {
      sidebar.classList.toggle('show');
      overlay.classList.toggle('show');
    }
  }

  function closeSidebar() {
    const sidebar = qs('#sidebar');
    const overlay = qs('#sidebarOverlay');
    if (sidebar && overlay) {
      sidebar.classList.remove('show');
      overlay.classList.remove('show');
    }
  }

  // Event delegation
  document.addEventListener('click', (e) => {
    if (e.target.closest('[data-action="toggle-sidebar"]')) {
      e.preventDefault();
      toggleSidebar();
    }
    if (e.target.closest('[data-action="close-sidebar"]')) {
      e.preventDefault();
      closeSidebar();
    }
  });
}

// Tooltips
export function initTooltips() {
  if (typeof bootstrap !== 'undefined') {
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
      return new bootstrap.Tooltip(tooltipTriggerEl);
    });
  }
}