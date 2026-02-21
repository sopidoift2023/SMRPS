const CACHE_NAME = 'smrps-pwa-v1';
const OFFLINE_URL = '/offline/';

// Install event - cache the offline page
self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => {
            return cache.addAll([
                OFFLINE_URL,
                '/static/logo1.png',
                '/static/background.jpg',
            ]);
        })
    );
});

// Activate event - clean up old caches
self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then((keyList) => {
            return Promise.all(keyList.map((key) => {
                if (key !== CACHE_NAME) {
                    return caches.delete(key);
                }
            }));
        })
    );
});

// Fetch event - network first, fallback to offline page
self.addEventListener('fetch', (event) => {
    if (event.request.mode === 'navigate') {
        event.respondWith(
            fetch(event.request)
                .catch(() => {
                    return caches.match(OFFLINE_URL);
                })
        );
    } else {
        // For non-navigation requests (assets), try network first, then cache
        event.respondWith(
            fetch(event.request)
                .catch(() => caches.match(event.request))
        );
    }
});
