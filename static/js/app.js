/* ===== ОБЩИЙ JAVASCRIPT ДЛЯ ВСЕХ СТРАНИЦ ===== */

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

// === Тема ===
(() => {
  const root = document.documentElement;
  const themeCheckbox = document.getElementById('theme');
  
  function applyTheme(theme){ 
    root.setAttribute('data-bs-theme', theme); 
    if (themeCheckbox) themeCheckbox.checked = theme === 'dark'; 
  }
  
  async function saveTheme(theme){ 
    try{ 
      await fetch('/set-theme',{
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body:JSON.stringify({theme})
      }); 
    } catch(e) {
      console.error('Error saving theme:', e);
    }
  }
  
  if (themeCheckbox){ 
    themeCheckbox.addEventListener('change', () => { 
      const next = themeCheckbox.checked ? 'dark' : 'light'; 
      applyTheme(next); 
      saveTheme(next); 
    }); 
  }
  
  applyTheme(root.getAttribute('data-bs-theme') || 'light');
})();

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