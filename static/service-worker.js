/* v1.0 — базовый SW: кэш оболочки + stale-while-revalidate для статики */
const CACHE_NAME = 'cb-shell-v1';
const SHELL = [
  '/', '/dashboard', '/expenses', '/categories', '/income',
  '/offline',
  '/static/css/clean-theme.css',
  'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css',
  'https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.0/font/bootstrap-icons.css'
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

/* Стратегии:
   • HTML-навигация: network-first с офлайн-фолбэком /offline
   • статика (css/js/png/svg/woff): stale-while-revalidate
   • любые не-GET запросы — пропускаем
*/
self.addEventListener('fetch', (e) => {
  const req = e.request;
  if (req.method !== 'GET') return;

  // HTML (переходы)
  if (req.mode === 'navigate') {
    e.respondWith(
      fetch(req)
        .then((res) => {
          const copy = res.clone();
          caches.open(CACHE_NAME).then((c) => c.put(req, copy));
          return res;
        })
        .catch(() =>
          caches.match(req).then((r) => r || caches.match('/offline'))
        )
    );
    return;
  }

  // статика
  const url = new URL(req.url);
  if (/\.(css|js|png|jpg|jpeg|svg|ico|webp|woff2?|ttf)$/i.test(url.pathname)) {
    e.respondWith(
      caches.match(req).then((cached) => {
        const net = fetch(req)
          .then((res) => {
            caches.open(CACHE_NAME).then((c) => c.put(req, res.clone()));
            return res;
          })
          .catch(() => cached);
        return cached || net;
      })
    );
  }
});