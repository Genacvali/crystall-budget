const CACHE = 'cb-app-v1';
const SHELL = [
  '/',
  '/static/vendor/bootstrap/bootstrap.min.css',
  '/static/vendor/bootstrap-icons/bootstrap-icons.css', 
  '/static/css/clean-theme.css',
  '/static/css/dashboard.css',
  '/static/js/bootstrap.bundle.min.js',
  '/static/vendor/bootstrap/bootstrap.bundle.min.js'
];

self.addEventListener('install', e => {
  e.waitUntil(
    caches.open(CACHE).then(c => c.addAll(SHELL))
  );
  self.skipWaiting();
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))
    )
  );
  self.clients.claim();
});


self.addEventListener('fetch', e => {
  const req = e.request;
  if (req.method !== 'GET') return; // POST/PUT/PATCH не трогаем здесь — они идут в «аутбокс» на клиенте

  e.respondWith(
    caches.match(req).then(hit => {
      const fetchPromise = fetch(req).then(res => {
        const copy = res.clone();
        caches.open(CACHE).then(c => c.put(req, copy));
        return res;
      }).catch(() => hit || caches.match('/')); // офлайн фоллбек
      return hit || fetchPromise;
    })
  );
});