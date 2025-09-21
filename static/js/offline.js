// /static/js/offline.js
(function(){
  const DB_NAME = 'cb-db';
  const STORE = 'outbox';

  function openDb() {
    return new Promise((resolve, reject) => {
      const req = indexedDB.open(DB_NAME, 1);
      req.onupgradeneeded = () => {
        const db = req.result;
        if (!db.objectStoreNames.contains(STORE)) {
          db.createObjectStore(STORE, { keyPath: 'id' });
        }
      };
      req.onsuccess = () => resolve(req.result);
      req.onerror = () => reject(req.error);
    });
  }
  
  async function outboxAdd(item){
    const db = await openDb();
    return new Promise((resolve,reject)=>{
      const tx = db.transaction(STORE,'readwrite');
      tx.objectStore(STORE).put(item);
      tx.oncomplete = resolve;
      tx.onerror = () => reject(tx.error);
    });
  }
  
  async function outboxAll(){
    const db = await openDb();
    return new Promise((resolve,reject)=>{
      const tx = db.transaction(STORE,'readonly');
      const req = tx.objectStore(STORE).getAll();
      req.onsuccess = () => resolve(req.result || []);
      req.onerror = () => reject(req.error);
    });
  }
  
  async function outboxDelete(id){
    const db = await openDb();
    return new Promise((resolve,reject)=>{
      const tx = db.transaction(STORE,'readwrite');
      tx.objectStore(STORE).delete(id);
      tx.oncomplete = resolve;
      tx.onerror = () => reject(tx.error);
    });
  }

  async function apiSend(method, url, body, headers = {'Content-Type':'application/json'}) {
    // добавляем идемпотентный operationId с клиента
    if (body && !body.operationId) {
      body.operationId = (crypto.randomUUID && crypto.randomUUID()) || String(Date.now())+'-'+Math.random();
    }
    
    try {
      const res = await fetch(url, {
        method, headers,
        body: body ? JSON.stringify(body) : undefined,
        credentials: 'include'
      });
      if (!res.ok) throw new Error('HTTP ' + res.status);
      return await res.json();
    } catch (err) {
      await outboxAdd({
        id: (crypto.randomUUID && crypto.randomUUID()) || String(Date.now())+'-'+Math.random(),
        method, url, body, headers,
        createdAt: Date.now()
      });
      return { queued: true };
    }
  }

  async function flushOutbox() {
    const items = await outboxAll();
    for (const item of items) {
      try {
        const res = await fetch(item.url, {
          method: item.method,
          headers: item.headers,
          body: item.body ? JSON.stringify(item.body) : undefined,
          credentials: 'include'
        });
        if (res.ok) {
          await outboxDelete(item.id);
        } else if (res.status === 401) {
          break; // треб. логин — не жжём очередь
        } else {
          break; // 4xx/5xx — оставим на потом
        }
      } catch {
        break; // сеть снова упала — выйдем
      }
    }
  }

  // авто-триггеры iOS-совместимые
  window.addEventListener('online', flushOutbox);
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible') flushOutbox();
  });
  
  // запрос на персистентность хранилища
  if (navigator.storage && navigator.storage.persist) {
    navigator.storage.persist();
  }
  
  // первый запуск
  flushOutbox();

  // экспорт в глобал
  window.CBOffline = { apiSend, flushOutbox };
})();