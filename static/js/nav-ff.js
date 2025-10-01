// nav-ff.js

// Тема (data-bs-theme + server sync) с синхронизацией двух переключателей
(() => {
  const root = document.documentElement;
  const toggle = document.getElementById('themeToggle');
  const toggleMobile = document.getElementById('themeToggleMobile');

  // Получаем текущую тему от сервера (из HTML)
  const initial = root.getAttribute('data-bs-theme') || 'light';
  
  // Синхронизируем состояние всех переключателей
  function syncToggles(theme) {
    const checked = theme === 'dark';
    if (toggle) toggle.checked = checked;
    if (toggleMobile) toggleMobile.checked = checked;
    
    // Update aria-checked для всех переключателей
    [toggle, toggleMobile].forEach(t => {
      if (t) {
        const switchLabel = t.closest('label[role="switch"]');
        if (switchLabel) {
          switchLabel.setAttribute('aria-checked', checked ? 'true' : 'false');
        }
      }
    });
  }

  // Инициализация
  syncToggles(initial);

  async function saveTheme(theme) {
    try {
      await fetch('/set-theme', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': document.querySelector('meta[name="csrf-token"]')?.content || ''
        },
        body: JSON.stringify({ theme })
      });
    } catch (e) {
      console.error('Error saving theme:', e);
    }
  }

  function changeTheme(newTheme) {
    root.setAttribute('data-bs-theme', newTheme);
    syncToggles(newTheme);
    saveTheme(newTheme);
  }

  // Обработчики для обоих переключателей
  if (toggle) {
    toggle.addEventListener('change', () => {
      const next = toggle.checked ? 'dark' : 'light';
      changeTheme(next);
    });
  }

  if (toggleMobile) {
    toggleMobile.addEventListener('change', () => {
      const next = toggleMobile.checked ? 'dark' : 'light';
      changeTheme(next);
    });
  }
})();

// Off-canvas (мобилка)
(() => {
  const btn = document.getElementById('navToggle');
  const close = document.getElementById('navClose');
  const panel = document.querySelector('.offcanvas-panel');
  const dim = document.getElementById('mobileDrawer');
  if (!btn || !panel || !dim) return;

  const open = () => {
    document.body.classList.add('offcanvas-open');
    panel.hidden = false; dim.hidden = false;
    btn.setAttribute('aria-expanded','true');
  };
  const hide = () => {
    document.body.classList.remove('offcanvas-open');
    btn.setAttribute('aria-expanded','false');
    setTimeout(() => { panel.hidden = true; dim.hidden = true; }, 200);
  };

  btn.addEventListener('click', open);
  dim.addEventListener('click', hide);
  if (close) close.addEventListener('click', hide);
  document.addEventListener('keydown', e => { if (e.key === 'Escape') hide(); });
})();

// Date picker functionality
(() => {
  const desktopDatePicker = document.getElementById('desktopDatePicker');
  const mobileDatePicker = document.getElementById('mobileDatePicker');

  if (!desktopDatePicker && !mobileDatePicker) return;

  function navigateToDate(dateStr) {
    // Extract year-month from date (YYYY-MM-DD -> YYYY-MM)
    const yearMonth = dateStr.slice(0, 7);
    const url = new URL(window.location);
    url.searchParams.set('ym', yearMonth);
    window.location.replace(url.toString());
  }

  // Event listeners for both date pickers
  if (desktopDatePicker) {
    desktopDatePicker.addEventListener('change', function() {
      if (this.value) {
        navigateToDate(this.value);
      }
    });
  }

  if (mobileDatePicker) {
    mobileDatePicker.addEventListener('change', function() {
      if (this.value) {
        navigateToDate(this.value);
      }
    });
  }
})();