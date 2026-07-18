/*
  Austin FloodOps Service Worker - PWA Offline FirstNet for Texas Field Ops
  Gov-grade: offline-first, queues approvals in IndexedDB, syncs when back online
  Lone Star State - Built for the Great State of Texas
*/
const CACHE_NAME = 'floodops-v0.4.0-texas';
const OFFLINE_URL = '/static/offline.html';
const CORE_ASSETS = [
  '/',
  '/static/index.html',
  '/static/manifest.json',
  '/health',
  '/api/events',
  '/api/heartbeat',
  'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css',
  'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js',
  'https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans:wght@400;500;600;700&display=swap'
];

self.addEventListener('install', (event) => {
  console.log('[FloodOps SW] Install - Great State of Texas, caching core assets');
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(CORE_ASSETS.map(url => new Request(url, {cache: 'reload'}))).catch(err => {
        console.warn('[FloodOps SW] Cache addAll failed, caching individually', err);
        // Try individual to avoid one failure breaking all
        return Promise.allSettled(CORE_ASSETS.map(url => cache.add(url).catch(e => console.warn('Failed', url, e))));
      });
    })
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  console.log('[FloodOps SW] Activate - cleaning old caches');
  event.waitUntil(
    caches.keys().then(keys => {
      return Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)));
    })
  );
  self.clients.claim();
});

// IndexedDB for offline approval queue - FirstNet field ops
const DB_NAME = 'floodops-offline-queue';
const STORE_NAME = 'pending-approvals';

function openDB() {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, 1);
    req.onupgradeneeded = (e) => {
      const db = e.target.result;
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        db.createObjectStore(STORE_NAME, {keyPath: 'incident_id'});
      }
    };
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

async function queueOfflineApproval(incident_id, action) {
  try {
    const db = await openDB();
    const tx = db.transaction(STORE_NAME, 'readwrite');
    tx.objectStore(STORE_NAME).put({
      incident_id,
      action, // approve/reject
      queued_at: new Date().toISOString(),
      actor_id: 'field-operator-firstnet',
      synced: false
    });
    console.log('[FloodOps SW] Queued offline', action, incident_id);
  } catch (e) {
    console.warn('[FloodOps SW] Queue failed', e);
  }
}

self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);

  // API requests - network First, fallback to cache, queue approvals offline
  if (url.pathname.startsWith('/api/')) {
    // For approve/reject, queue if offline
    if ((url.pathname.includes('/approve') || url.pathname.includes('/reject')) && event.request.method === 'POST') {
      event.respondWith(
        fetch(event.request.clone()).catch(async () => {
          // Offline - queue
          const incident_id = url.pathname.split('/')[3] || 'unknown';
          const action = url.pathname.includes('/approve') ? 'approve' : 'reject';
          await queueOfflineApproval(incident_id, action);
          return new Response(JSON.stringify({
            status: 'queued_offline',
            incident_id,
            detail: 'Offline - approval queued in IndexedDB for FirstNet sync when back online. Texas gov offline-first.',
            queued_at: new Date().toISOString()
          }), {headers: {'Content-Type': 'application/json'}});
        })
      );
      return;
    }

    // Other APIs: network first
    event.respondWith(
      fetch(event.request)
        .then(resp => {
          // Cache successful GETs
          if (event.request.method === 'GET' && resp.ok) {
            const clone = resp.clone();
            caches.open(CACHE_NAME).then(cache => cache.put(event.request, clone));
          }
          return resp;
        })
        .catch(() => {
          return caches.match(event.request).then(cached => {
            if (cached) return cached;
            return new Response(JSON.stringify({error: 'Offline - cached data only, Texas field ops mode'}), {headers: {'Content-Type': 'application/json'}, status: 503});
          });
        })
    );
    return;
  }

  // Navigation requests - cache first, show offline page if needed
  if (event.request.mode === 'navigate') {
    event.respondWith(
      fetch(event.request).catch(() => {
        return caches.match('/').then(cached => cached || caches.match(OFFLINE_URL));
      })
    );
    return;
  }

  // Static assets - cache first
  event.respondWith(
    caches.match(event.request).then(cached => {
      if (cached) return cached;
      return fetch(event.request).then(resp => {
        if (resp.ok && event.request.method === 'GET') {
          const clone = resp.clone();
          caches.open(CACHE_NAME).then(cache => cache.put(event.request, clone));
        }
        return resp;
      }).catch(() => {
        // Return offline placeholder for images etc
        return new Response('Offline - Great State of Texas Field Mode', {status: 503, headers: {'Content-Type': 'text/plain'}});
      });
    })
  );
});

self.addEventListener('sync', (event) => {
  if (event.tag === 'floodops-sync-approvals') {
    console.log('[FloodOps SW] Background sync approvals - FirstNet');
    event.waitUntil(syncOfflineQueue());
  }
});

async function syncOfflineQueue() {
  try {
    const db = await openDB();
    const tx = db.transaction(STORE_NAME, 'readwrite');
    const store = tx.objectStore(STORE_NAME);
    const all = await new Promise((res, rej) => {
      const req = store.getAll();
      req.onsuccess = () => res(req.result);
      req.onerror = () => rej(req.error);
    });
    for (const item of all) {
      if (item.synced) continue;
      try {
        const resp = await fetch(`/api/decisions/${item.incident_id}/${item.action}`, {method: 'POST'});
        if (resp.ok) {
          item.synced = true;
          item.synced_at = new Date().toISOString();
          store.put(item);
          console.log('[FloodOps SW] Synced queued', item.action, item.incident_id);
        }
      } catch (e) {
        console.warn('[FloodOps SW] Sync failed for', item.incident_id, e);
      }
    }
  } catch (e) {
    console.warn('[FloodOps SW] Sync queue open failed', e);
  }
}

console.log('[FloodOps SW] Loaded - Built for the Great State of Texas ⭐ TDEM Ready');
