/* ===== ОБЩИЙ JAVASCRIPT ДЛЯ ВСЕХ СТРАНИЦ ===== */

// === CSRF Protection для всех fetch запросов ===
(() => {
  // Сохраняем оригинальный fetch
  const originalFetch = window.fetch;
  
  // Получаем CSRF токен из мета-тега
  const getCSRFToken = () => {
    const meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.getAttribute('content') : null;
  };
  
  // Перехватчик для fetch
  window.fetch = function(url, options = {}) {
    const token = getCSRFToken();
    
    // Проверяем, нужен ли CSRF токен
    const method = (options.method || 'GET').toUpperCase();
    const needsCSRF = ['POST', 'PUT', 'PATCH', 'DELETE'].includes(method);
    
    if (needsCSRF && token) {
      // Подготавливаем headers
      const headers = new Headers(options.headers || {});
      
      // Добавляем X-CSRF-Token если его еще нет
      if (!headers.has('X-CSRF-Token')) {
        headers.set('X-CSRF-Token', token);
      }
      
      // Создаем новые опции с CSRF заголовком
      options = {
        ...options,
        headers: headers
      };
    }
    
    // Вызываем оригинальный fetch
    return originalFetch.call(this, url, options);
  };
})();

// === Нормализация decimal для RU-локали ===
(() => {
  // Функция для нормализации числа (замена запятой на точку)
  const normalizeDecimal = (value) => {
    if (typeof value === 'string') {
      return value.replace(',', '.');
    }
    return value;
  };

  // Инициализация при загрузке DOM
  document.addEventListener('DOMContentLoaded', () => {
    // Находим все поля ввода чисел
    const numberInputs = document.querySelectorAll('input[type="number"], input[inputmode="decimal"]');
    
    numberInputs.forEach(input => {
      // Обработка при вводе - заменяем запятую на точку в реальном времени
      input.addEventListener('input', (e) => {
        const originalValue = e.target.value;
        const normalizedValue = normalizeDecimal(originalValue);
        
        if (originalValue !== normalizedValue) {
          // Сохраняем позицию курсора
          const selectionStart = e.target.selectionStart;
          const selectionEnd = e.target.selectionEnd;
          
          e.target.value = normalizedValue;
          
          // Восстанавливаем позицию курсора
          e.target.setSelectionRange(selectionStart, selectionEnd);
        }
      });
      
      // Обработка при потере фокуса - финальная нормализация
      input.addEventListener('blur', (e) => {
        e.target.value = normalizeDecimal(e.target.value);
      });
      
      // Обработка перед отправкой формы
      const form = input.closest('form');
      if (form && !form.dataset.decimalNormalized) {
        form.dataset.decimalNormalized = 'true';
        
        form.addEventListener('submit', () => {
          const allNumberInputs = form.querySelectorAll('input[type="number"], input[inputmode="decimal"]');
          allNumberInputs.forEach(inp => {
            inp.value = normalizeDecimal(inp.value);
          });
        });
      }
    });
  });
  
  // Экспортируем функцию для использования в других скриптах
  window.normalizeDecimal = normalizeDecimal;
})();

// === Дроп-календарь ===
(() => {
  const root  = document.getElementById('datePicker');
  const btn   = document.getElementById('dpBtn');
  const grid  = document.getElementById('dpGrid');
  const title = document.getElementById('dpTitle');
  const label = document.getElementById('dpLabel');
  if (!root || !btn || !grid || !title || !label) return;

  const months = ['Январь','Февраль','Март','Апрель','Май','Июнь','Июль','Август','Сентябрь','Октябрь','Ноябрь','Декабрь'];
  const dows   = ['Пн','Вт','Ср','Чт','Пт','Сб','Вс'];
  const targets = ['#expenseDate','#incomeDate'];
  let current = new Date(); current.setDate(1);
  let selected = new Date();
  const ymd = d => d.toISOString().slice(0,10);
  const fmt = d => d.toLocaleDateString('ru-RU',{day:'2-digit',month:'2-digit',year:'numeric'});

  function render(){
    const y=current.getFullYear(), m=current.getMonth();
    title.textContent = `${months[m]} ${y}`;
    const first = new Date(y,m,1);
    const firstDow = (first.getDay()+6)%7;
    const dim = new Date(y,m+1,0).getDate();
    const total = 42;
    const today = ymd(new Date());
    const frag = document.createDocumentFragment();

    dows.forEach(d => { 
      const el = document.createElement('div'); 
      el.className='dp-dow'; 
      el.textContent=d; 
      frag.appendChild(el); 
    });

    for (let i=0;i<total;i++){
      const dayNum = i - firstDow + 1;
      const date = new Date(y,m,dayNum);
      const out = dayNum < 1 || dayNum > dim;
      const cell = document.createElement('div');
      cell.className = 'dp-day';
      if (out) cell.classList.add('dp-out');
      const ds = ymd(date);
      if (ds === today) cell.classList.add('dp-today');
      if (ymd(selected) === ds) cell.classList.add('dp-sel');
      cell.textContent = String(date.getDate());
      cell.addEventListener('click', () => {
        selected = date; 
        label.textContent = fmt(date);
        targets.forEach(sel => { 
          const i = document.querySelector(sel); 
          if (i) i.value = ds; 
        });
        close();
      });
      frag.appendChild(cell);
    }
    grid.replaceChildren(frag);
  }
  
  function open(){ 
    root.classList.add('open'); 
    render(); 
    trap=true; 
  }
  
  function close(){ 
    root.classList.remove('open'); 
    trap=false; 
  }
  
  btn.addEventListener('click', (e)=>{ 
    e.stopPropagation(); 
    root.classList.contains('open') ? close() : open(); 
  });
  
  document.getElementById('dpPrev')?.addEventListener('click', ()=>{ 
    current.setMonth(current.getMonth()-1); 
    render(); 
  });
  
  document.getElementById('dpNext')?.addEventListener('click', ()=>{ 
    current.setMonth(current.getMonth()+1); 
    render(); 
  });
  
  document.getElementById('dpToday')?.addEventListener('click', ()=>{ 
    current=new Date(); 
    current.setDate(1); 
    selected=new Date(); 
    render(); 
  });
  
  let trap=false;
  document.addEventListener('click', (e)=>{ 
    if (!root.contains(e.target) && trap) close(); 
  });
  
  document.addEventListener('keydown', (e)=>{ 
    if (e.key==='Escape' && trap) close(); 
  });
  
  label.textContent = fmt(selected);
})();

// === Тема (удалено - используется nav-ff.js) ===

// === Пользовательское меню ===
(() => {
  const userMenu = document.querySelector('.cb-user');
  const userBtn = document.querySelector('.cb-user-btn');
  
  if (!userMenu || !userBtn) return;
  
  let isOpen = false;
  
  function open() {
    userMenu.classList.add('open');
    isOpen = true;
  }
  
  function close() {
    userMenu.classList.remove('open');
    isOpen = false;
  }
  
  userBtn.addEventListener('click', (e) => {
    e.preventDefault();
    e.stopPropagation();
    isOpen ? close() : open();
  });
  
  document.addEventListener('click', (e) => {
    if (!userMenu.contains(e.target) && isOpen) {
      close();
    }
  });
  
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && isOpen) {
      close();
    }
  });
})();

// === Функция для показа уведомлений ===
function showToast(message, type = 'info') {
  const toast = document.createElement('div');
  toast.className = `alert alert-${type} position-fixed`;
  toast.style.cssText = 'top: 20px; right: 20px; z-index: 1050; min-width: 300px;';
  toast.textContent = message;
  document.body.appendChild(toast);
  setTimeout(() => toast.remove(), 4000);
}

// === Глобальная функция для подтверждения удаления через модалку ===
window.confirmDelete = function(message, onConfirm) {
  const modal = new bootstrap.Modal(document.getElementById('confirmDeleteModal'));
  const messageEl = document.getElementById('confirmDeleteMessage');
  const confirmBtn = document.getElementById('confirmDeleteBtn');
  
  messageEl.textContent = message;
  
  // Удаляем старые обработчики
  const newConfirmBtn = confirmBtn.cloneNode(true);
  confirmBtn.parentNode.replaceChild(newConfirmBtn, confirmBtn);
  
  // Добавляем новый обработчик
  newConfirmBtn.addEventListener('click', () => {
    modal.hide();
    onConfirm();
  });
  
  modal.show();
};

// === Современный Drawer ===
(() => {
  const body = document.body;
  const drawer = document.getElementById('drawer');
  const dim = document.getElementById('dim');
  const openBtn = document.getElementById('openDrawer');
  const closeBtn = document.getElementById('closeDrawer');

  if (!drawer || !dim || !openBtn || !closeBtn) return;

  function openDrawer() {
    body.classList.add('drawer-open');
    drawer.hidden = false; 
    dim.hidden = false;
    // перенос фокуса внутрь
    setTimeout(() => closeBtn.focus(), 0);
  }
  
  function closeDrawer() {
    body.classList.remove('drawer-open');
    // по окончании анимации прячем в DOM (для скринридеров)
    setTimeout(() => { 
      drawer.hidden = true; 
      dim.hidden = true; 
    }, 260);
  }
  
  openBtn.addEventListener('click', openDrawer);
  closeBtn.addEventListener('click', closeDrawer);
  dim.addEventListener('click', closeDrawer);
  document.addEventListener('keydown', (e) => { 
    if (e.key === 'Escape') closeDrawer(); 
  });

  // Закрытие при клике на ссылки навигации
  drawer.addEventListener('click', (e) => {
    const link = e.target.closest('a.cb-drawer-item');
    if (link) closeDrawer();
  });

  // Скрываем drawer изначально
  drawer.hidden = true;
  dim.hidden = true;
})();

/* === Переключатель темы (удалено - используется nav-ff.js) === */

/* === Валюта из select внутри drawer === */
async function updateCurrency(code){
  try { await fetch(`/set-currency/${encodeURIComponent(code)}`, {method:'GET'}); }
  catch(e){}
  location.reload();
}

// === Функция для обновления валюты ===
function updateCurrency(currency) {
  fetch('/set-currency', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ currency: currency })
  })
  .then(response => response.json())
  .then(data => {
    if (data.success) {
      // Обновляем основной селектор валюты, если он есть
      const mainCurrencySelect = document.querySelector('#currency-selector');
      if (mainCurrencySelect) {
        mainCurrencySelect.value = currency;
      }
      // Можно добавить уведомление об успешном изменении
      console.log('Currency updated to:', currency);
    }
  })
  .catch(error => {
    console.error('Failed to update currency:', error);
  });
}