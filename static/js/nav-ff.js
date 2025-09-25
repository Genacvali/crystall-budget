// nav-ff.js

// Тема (data-bs-theme + server sync)
(() => {
  const root = document.documentElement;
  const toggle = document.getElementById('themeToggle');
  if (!toggle) return;

  // Получаем текущую тему от сервера (из HTML)
  const initial = root.getAttribute('data-bs-theme') || 'light';
  toggle.checked = initial === 'dark';

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

  toggle.addEventListener('change', () => {
    const next = toggle.checked ? 'dark' : 'light';
    root.setAttribute('data-bs-theme', next);
    
    // Сохраняем на сервер
    saveTheme(next);
    
    // Update aria-checked on the switch label
    const switchLabel = toggle.closest('label[role="switch"]');
    if (switchLabel) {
      switchLabel.setAttribute('aria-checked', toggle.checked ? 'true' : 'false');
    }
  });
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