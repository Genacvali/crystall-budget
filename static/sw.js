// Crystal Budget Service Worker
// Версия: v6-static-only
const CACHE_NAME = 'crystalbudget-static-v6';
const RUNTIME_CACHE = 'crystalbudget-runtime-v6';

// Статические ресурсы для кэширования
// Эти URL будут обновляться автоматически с новыми хэшами
const STATIC_RESOURCES = [
  '/static/css/clean-theme.css',
  '/static/css/app.css',
  '/static/css/drawer.css',
  '/static/css/dashboard.css',
  '/static/js/app.js',
  '/static/js/modules/ui.js',
  '/static/js/modules/forms.js',
  '/static/js/modules/swipe.js',
  '/static/js/entries/dashboard.entry.js',
  '/static/js/entries/expenses.entry.js',
  '/static/js/entries/income.entry.js',
  '/static/js/entries/categories.entry.js',
  '/static/js/progress_bars.js',
  '/static/js/dashboard-cats.js',
  '/static/icons/icon-192.png',
  '/static/icons/icon-512.png',
  '/static/icons/favicon.ico',
  '/static/manifest.json',
  '/static/manifest.webmanifest'
];

// Установка Service Worker
self.addEventListener('install', function(event) {
  console.log('[SW] Installing v6 - static only caching');
  
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        console.log('[SW] Precaching static resources');
        return cache.addAll(STATIC_RESOURCES);
      })
      .then(() => {
        console.log('[SW] Static resources cached successfully');
        return self.skipWaiting();
      })
      .catch(error => {
        console.error('[SW] Failed to cache static resources:', error);
      })
  );
});

// Активация Service Worker
self.addEventListener('activate', function(event) {
  console.log('[SW] Activating v6');
  
  event.waitUntil(
    Promise.all([
      // Очистка старых кэшей
      caches.keys().then(cacheNames => {
        return Promise.all(
          cacheNames
            .filter(cacheName => 
              cacheName !== CACHE_NAME && 
              cacheName !== RUNTIME_CACHE &&
              cacheName.startsWith('crystalbudget-')
            )
            .map(cacheName => {
              console.log('[SW] Deleting old cache:', cacheName);
              return caches.delete(cacheName);
            })
        );
      }),
      // Взятие контроля над всеми клиентами
      self.clients.claim()
    ])
  );
});

// Обработка запросов
self.addEventListener('fetch', function(event) {
  const url = new URL(event.request.url);
  
  // Игнорируем запросы с других доменов
  if (url.origin !== location.origin) {
    return;
  }

  // Стратегия кэширования в зависимости от типа ресурса
  if (isStaticResource(event.request)) {
    // Статические ресурсы: Cache First
    event.respondWith(cacheFirstStrategy(event.request));
  } else if (isAPIRequest(event.request)) {
    // API запросы: Network First с коротким кэшем
    event.respondWith(networkFirstStrategy(event.request));
  } else {
    // HTML страницы: Network Only (всегда свежие, приватные данные)
    event.respondWith(networkOnlyStrategy(event.request));
  }
});

// Проверка, является ли запрос статическим ресурсом
function isStaticResource(request) {
  const url = new URL(request.url);
  return url.pathname.startsWith('/static/') || 
         url.pathname === '/manifest.json' ||
         url.pathname === '/manifest.webmanifest';
}

// Проверка, является ли запрос API запросом
function isAPIRequest(request) {
  const url = new URL(request.url);
  return url.pathname.startsWith('/api/') || 
         url.pathname.includes('.json');
}

// Стратегия Cache First для статических ресурсов
async function cacheFirstStrategy(request) {
  try {
    const cachedResponse = await caches.match(request);
    if (cachedResponse) {
      console.log('[SW] Cache hit for:', request.url);
      return cachedResponse;
    }
    
    console.log('[SW] Cache miss for:', request.url);
    const networkResponse = await fetch(request);
    
    // Кэшируем только успешные ответы
    if (networkResponse.ok) {
      const cache = await caches.open(CACHE_NAME);
      cache.put(request, networkResponse.clone());
    }
    
    return networkResponse;
  } catch (error) {
    console.error('[SW] Cache first strategy failed:', error);
    // Пытаемся вернуть из кэша если сеть недоступна
    const cachedResponse = await caches.match(request);
    if (cachedResponse) {
      return cachedResponse;
    }
    throw error;
  }
}

// Стратегия Network First для API запросов
async function networkFirstStrategy(request) {
  try {
    const networkResponse = await fetch(request);
    
    // Кэшируем только GET запросы с успешными ответами
    if (request.method === 'GET' && networkResponse.ok) {
      const cache = await caches.open(RUNTIME_CACHE);
      cache.put(request, networkResponse.clone());
    }
    
    return networkResponse;
  } catch (error) {
    console.warn('[SW] Network failed, trying cache for:', request.url);
    const cachedResponse = await caches.match(request);
    if (cachedResponse) {
      return cachedResponse;
    }
    throw error;
  }
}

// Стратегия Network Only для HTML страниц
async function networkOnlyStrategy(request) {
  // Всегда идём в сеть для HTML страниц с приватными данными
  return fetch(request);
}

// Обработка сообщений от клиента
self.addEventListener('message', function(event) {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    console.log('[SW] Received SKIP_WAITING message');
    self.skipWaiting();
  } else if (event.data && event.data.type === 'CLEAR_CACHE') {
    console.log('[SW] Clearing all caches');
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.map(cacheName => caches.delete(cacheName))
      );
    });
  }
});

console.log('[SW] Crystal Budget Service Worker v6 loaded - static assets only');