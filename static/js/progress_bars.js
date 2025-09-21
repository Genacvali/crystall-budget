(function(){
  const list = document.getElementById('catList');
  if(!list) return;

  function sortCats(key, asc){
    const items = Array.from(list.querySelectorAll('article.cat'));
    const dir = asc ? 1 : -1;
    const val = (el) => {
      switch(key){
        case 'manual':   return Number(el.dataset.order || 0);
        case 'name':     return (el.dataset.name || '').toLowerCase();
        case 'progress': return Number(el.dataset.progress || 0);
        case 'remaining':return Number(el.dataset.remaining || 0);
        case 'spent':    return Number(el.dataset.spent || 0);
        case 'limit':    return Number(el.dataset.limit || 0);
        default:         return 0;
      }
    };
    items.sort((a,b)=>{
      const va = val(a), vb = val(b);
      if(typeof va === 'string' || typeof vb === 'string'){
        return va.localeCompare(vb) * dir;
      }
      return (va - vb) * dir;
    });
    items.forEach(el=>list.appendChild(el));
  }

  // направление
  const dirBtn = document.getElementById('sortDirBtn');
  let asc = true;
  dirBtn?.addEventListener('click', ()=>{
    asc = !asc;
    dirBtn.dataset.dir = asc ? 'asc' : 'desc';
    const key = document.querySelector('.dropdown-item.active')?.dataset.key || 'manual';
    sortCats(key, asc);
  });

  // выбор ключа
  document.querySelectorAll('.dropdown-menu .sort-opt').forEach(btn=>{
    btn.addEventListener('click', (e)=>{
      document.querySelectorAll('.dropdown-menu .sort-opt').forEach(b=>b.classList.remove('active'));
      btn.classList.add('active');
      document.getElementById('sortKeyLabel').textContent = btn.textContent.trim();
      sortCats(btn.dataset.key, asc);
    });
  });
})();