// nav-ff.js

// Тема (data-bs-theme + localStorage)
(() => {
  const root = document.documentElement;
  const toggle = document.getElementById('themeToggle');
  if (!toggle) return;

  const saved = localStorage.getItem('cb-theme');
  const initial = saved || root.getAttribute('data-bs-theme') || 'dark'; // начнём с dark как на проде
  root.setAttribute('data-bs-theme', initial);
  toggle.checked = initial === 'dark';

  toggle.addEventListener('change', () => {
    const next = toggle.checked ? 'dark' : 'light';
    root.setAttribute('data-bs-theme', next);
    localStorage.setItem('cb-theme', next);
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