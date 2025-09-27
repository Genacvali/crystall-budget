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

// Month picker functionality
(() => {
  const monthPicker = document.getElementById('monthPicker');
  const mobileMonthPicker = document.getElementById('mobileMonthPicker');
  const currentMonthLabel = document.getElementById('currentMonthLabel');
  const mobileMonthLabel = document.getElementById('mobileMonthLabel');

  if (!monthPicker && !mobileMonthPicker) return;

  // Get current month from URL or default
  const urlParams = new URLSearchParams(window.location.search);
  let currentMonth = urlParams.get('month') || new Date().toISOString().slice(0, 7); // YYYY-MM format

  // Month names in Russian
  const monthNames = [
    'Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
    'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь'
  ];

  function formatMonthLabel(monthStr) {
    const [year, month] = monthStr.split('-');
    const monthIndex = parseInt(month) - 1;
    return `${monthNames[monthIndex]} ${year}`;
  }

  function updateLabels() {
    const label = formatMonthLabel(currentMonth);
    if (currentMonthLabel) currentMonthLabel.textContent = label;
    if (mobileMonthLabel) mobileMonthLabel.textContent = label;
  }

  function createMonthPicker() {
    const picker = document.createElement('div');
    picker.className = 'month-picker-dropdown';
    picker.innerHTML = `
      <div class="month-picker-content">
        <div class="month-picker-header">
          <button type="button" class="btn btn-sm btn-outline-secondary" id="prevYear">&laquo;</button>
          <span class="year-label" id="yearLabel">2024</span>
          <button type="button" class="btn btn-sm btn-outline-secondary" id="nextYear">&raquo;</button>
        </div>
        <div class="month-grid">
          ${monthNames.map((name, index) => 
            `<button type="button" class="month-btn" data-month="${index + 1}">${name.slice(0, 3)}</button>`
          ).join('')}
        </div>
        <div class="month-picker-footer">
          <button type="button" class="btn btn-sm btn-secondary" id="monthPickerClose">Закрыть</button>
        </div>
      </div>
    `;

    // Add styles
    const style = document.createElement('style');
    style.textContent = `
      .month-picker-dropdown {
        position: absolute;
        top: 100%;
        right: 0;
        width: 280px;
        max-width: 95vw;
        background: var(--bs-body-bg);
        border: 1px solid var(--bs-border-color);
        border-radius: 12px;
        box-shadow: 0 8px 24px rgba(0,0,0,.15);
        backdrop-filter: blur(8px);
        z-index: 1080;
        margin-top: 8px;
        display: none;
      }
      :root[data-bs-theme="light"] .month-picker-dropdown {
        background: rgba(255,255,255,.95);
        border-color: var(--bs-border-color);
        box-shadow: 0 8px 24px rgba(0,0,0,.12);
        color: rgba(30,39,50,.8);
      }
      :root[data-bs-theme="dark"] .month-picker-dropdown {
        background: rgba(34,37,41,.95);
        border-color: var(--bs-border-color);
        color: rgba(231,236,243,.8);
      }
      .month-picker-content {
        padding: 16px;
      }
      .month-picker-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 12px;
        padding: 0 4px;
      }
      .month-picker-header .btn {
        width: 32px;
        height: 32px;
        padding: 0;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 14px;
        border-radius: 6px;
        min-width: 32px;
        border: 1px solid var(--bs-border-color);
      }
      .year-label {
        font-weight: 600;
        font-size: 15px;
        color: var(--bs-body-color);
        user-select: none;
      }
      .month-grid {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 8px;
        margin-bottom: 12px;
      }
      .month-btn {
        padding: 8px 4px;
        border: 1px solid transparent;
        border-radius: 6px;
        background: transparent;
        cursor: pointer;
        transition: all .15s ease;
        font-size: 14px;
        color: var(--bs-body-color);
        min-height: 38px;
        position: relative;
        overflow: hidden;
      }
      .month-btn:hover {
        background: rgba(var(--bs-primary-rgb),.1);
        border-color: var(--bs-primary);
        color: var(--bs-primary);
      }
      .month-btn.active {
        background: var(--bs-primary);
        color: white;
        border-color: var(--bs-primary);
        font-weight: 600;
      }
      .month-btn:focus-visible {
        outline: 2px solid var(--bs-primary);
        outline-offset: 2px;
      }
      .month-picker-footer {
        display: flex;
        justify-content: center;
        padding-top: 8px;
        border-top: 1px solid var(--bs-border-color);
      }
      .month-picker-footer .btn {
        font-size: 12px;
        padding: 6px 16px;
        height: 32px;
        border-radius: 6px;
      }
      
      @media (max-width: 575.98px) {
        .month-picker-dropdown {
          position: fixed;
          top: 50% !important;
          left: 50% !important;
          right: auto !important;
          transform: translate(-50%, -50%);
          width: 300px;
          max-width: 92vw;
          max-height: 85vh;
          border-radius: 16px;
          box-shadow: 0 12px 40px rgba(0,0,0,.25);
        }
        .month-picker-content {
          padding: 20px;
        }
        .month-picker-header {
          margin-bottom: 16px;
          padding: 0 8px;
        }
        .month-picker-header .btn {
          width: 40px;
          height: 40px;
          font-size: 16px;
          border-radius: 8px;
          min-width: 40px;
        }
        .year-label {
          font-size: 18px;
          font-weight: 700;
        }
        .month-grid {
          gap: 12px;
          margin-bottom: 20px;
        }
        .month-btn {
          min-height: 48px;
          font-size: 15px;
          padding: 12px 8px;
          border-radius: 8px;
          font-weight: 500;
          border-width: 2px;
        }
        .month-btn:hover,
        .month-btn:focus {
          transform: scale(1.05);
        }
        .month-btn.active {
          box-shadow: 0 4px 12px rgba(var(--bs-primary-rgb),.3);
        }
        .month-picker-footer {
          padding-top: 16px;
          border-top: 2px solid var(--bs-border-color);
        }
        .month-picker-footer .btn {
          font-size: 14px;
          padding: 12px 24px;
          height: 44px;
          border-radius: 8px;
          font-weight: 600;
        }
      }
    `;
    document.head.appendChild(style);

    return picker;
  }

  const picker = createMonthPicker();
  document.body.appendChild(picker);

  let currentYear = parseInt(currentMonth.split('-')[0]);
  let selectedMonth = parseInt(currentMonth.split('-')[1]);

  function updatePicker() {
    const yearLabel = picker.querySelector('#yearLabel');
    const monthButtons = picker.querySelectorAll('.month-btn');

    if (yearLabel) yearLabel.textContent = currentYear;

    monthButtons.forEach((btn, index) => {
      btn.classList.toggle('active', index + 1 === selectedMonth && currentYear === parseInt(currentMonth.split('-')[0]));
    });
  }

  function showPicker(button) {
    const rect = button.getBoundingClientRect();
    picker.style.display = 'block';
    picker.style.top = `${rect.bottom + window.scrollY}px`;
    picker.style.left = `${rect.right - picker.offsetWidth + window.scrollX}px`;
    updatePicker();
  }

  function hidePicker() {
    picker.style.display = 'none';
  }

  function navigateToMonth(year, month) {
    const monthStr = `${year}-${month.toString().padStart(2, '0')}`;
    const url = new URL(window.location);
    url.searchParams.set('month', monthStr);
    window.location.href = url.toString();
  }

  // Event listeners
  if (monthPicker) {
    const btn = monthPicker.querySelector('.ff-month-btn');
    if (btn) {
      btn.addEventListener('click', () => showPicker(btn));
    }
  }

  if (mobileMonthPicker) {
    mobileMonthPicker.addEventListener('click', () => showPicker(mobileMonthPicker));
  }

  // Picker event listeners
  picker.addEventListener('click', (e) => {
    if (e.target.id === 'prevYear') {
      currentYear--;
      updatePicker();
    } else if (e.target.id === 'nextYear') {
      currentYear++;
      updatePicker();
    } else if (e.target.classList.contains('month-btn')) {
      const month = parseInt(e.target.dataset.month);
      navigateToMonth(currentYear, month);
    } else if (e.target.id === 'monthPickerClose') {
      hidePicker();
    }
  });

  // Close picker when clicking outside
  document.addEventListener('click', (e) => {
    if (!monthPicker?.contains(e.target) && !mobileMonthPicker?.contains(e.target) && !picker.contains(e.target)) {
      hidePicker();
    }
  });

  // Initialize labels
  updateLabels();
})();