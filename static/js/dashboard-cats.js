document.addEventListener('DOMContentLoaded', () => {
  const list    = document.getElementById('catList');
  const dirBtn  = document.getElementById('sortDirBtn');
  const keyBtns = document.querySelectorAll('.sort-opt');
  const keyLabel= document.getElementById('sortKeyLabel');

  let sortKey = 'manual';
  let dir     = dirBtn?.dataset.dir || 'asc';

  function val(el, key){
    if (key === 'name') return (el.dataset.name || '').toLowerCase();
    return Number(el.dataset[key] || 0);
  }

  function applySort(){
    if (!list) return;
    const items = Array.from(list.children);
    if (sortKey === 'manual'){
      items.sort((a,b)=> (Number(a.dataset.order||0) - Number(b.dataset.order||0)));
    } else {
      items.sort((a,b)=> {
        const av = val(a, sortKey), bv = val(b, sortKey);
        return av === bv ? 0 : (av > bv ? 1 : -1);
      });
    }
    if (dir === 'desc') items.reverse();
    const frag = document.createDocumentFragment();
    items.forEach(it => frag.appendChild(it));
    list.appendChild(frag);
  }

  keyBtns.forEach(btn => btn.addEventListener('click', e => {
    sortKey = e.currentTarget.dataset.key;
    keyLabel.textContent = e.currentTarget.textContent;
    applySort();
  }));

  dirBtn?.addEventListener('click', () => {
    dir = dir === 'asc' ? 'desc' : 'asc';
    dirBtn.dataset.dir = dir; // повернёт иконку в CSS
    applySort();
  });

  applySort();
});
