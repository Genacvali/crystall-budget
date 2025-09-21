// static/js/progress-bars.js
document.addEventListener('DOMContentLoaded', () => {
  const list = document.getElementById('catList');
  const sortDrop  = document.getElementById('sortDrop');
  const sortKeyBtn= document.getElementById('sortKeyBtn');
  const sortLabel = document.getElementById('sortLabel');
  const dirBtn    = document.getElementById('dirBtn');

  if (!list) return;

  const state = { key: 'manual', dir: 1 };

  function getVal(el, key){
    const v = el.dataset[key];
    if (key === 'name') return (v || '').toString();
    return parseFloat(v || '0');
  }

  function applySort(){
    if (state.key === 'manual') return; // серверный порядок
    const items = Array.from(list.querySelectorAll('.cat-item'));
    items.sort((a,b)=>{
      const A = getVal(a, state.key);
      const B = getVal(b, state.key);
      if (typeof A === 'string') return state.dir * A.localeCompare(B, 'ru');
      return state.dir * (A - B);
    });
    items.forEach(n => list.appendChild(n));
  }

  // направление
  dirBtn?.addEventListener('click', ()=>{
    state.dir *= -1;
    applySort();
  });

  // раскрытие меню
  sortKeyBtn?.addEventListener('click', ()=>{
    const open = sortDrop.getAttribute('data-open') === '1';
    sortDrop.setAttribute('data-open', open ? '0' : '1');
    sortKeyBtn.setAttribute('aria-expanded', (!open).toString());
  });

  // выбор ключа
  sortDrop?.querySelectorAll('.seg-item').forEach(it=>{
    it.addEventListener('click', ()=>{
      state.key = it.dataset.key;
      sortLabel.textContent = it.textContent;
      sortDrop.setAttribute('data-open','0');
      sortKeyBtn.setAttribute('aria-expanded','false');
      applySort();
    });
  });

  // клик вне меню — закрыть
  document.addEventListener('click', (e)=>{
    if (!sortDrop.contains(e.target)) {
      sortDrop.setAttribute('data-open','0');
      sortKeyBtn.setAttribute('aria-expanded','false');
    }
  });
});