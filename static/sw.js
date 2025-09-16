const CACHE_NAME = 'cb-shell-v1';
const SHELL = [
  '/', '/dashboard', '/expenses', '/categories', '/income',
  '/static/css/clean-theme.css',
  '/static/vendor/bootstrap/bootstrap.min.css',
  '/static/vendor/bootstrap-icons/bootstrap-icons.css',
  '/static/vendor/bootstrap-icons/bootstrap-icons.woff2'
];

self.addEventListener('install', (e) => {
  e.waitUntil(caches.open(CACHE_NAME).then(c => c.addAll(SHELL)));
  self.skipWaiting();
});

self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener('fetch', (e) => {
  const req = e.request;
  if (req.method !== 'GET') return;

  // HTML (navigation): network first
  if (req.mode === 'navigate') {
    e.respondWith(
      fetch(req).then(res => {
        caches.open(CACHE_NAME).then(c => c.put(req, res.clone()));
        return res;
      }).catch(() => caches.match(req))
    );
    return;
  }

  // static assets: stale-while-revalidate
  if (/\.(css|js|png|jpg|jpeg|svg|ico|woff2?)$/i.test(new URL(req.url).pathname)) {
    e.respondWith(
      caches.match(req).then(cached => {
        const net = fetch(req).then(res => {
          caches.open(CACHE_NAME).then(c => c.put(req, res.clone()));
          return res;
        }).catch(() => cached);
        return cached || net;
      })
    );
  }
});