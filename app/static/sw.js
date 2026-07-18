/*
  Austin FloodOps Service Worker - offline continuity prototype
  Caches dashboard assets and preserves browser-local action drafts for review
  Lone Star State - Built for the Great State of Texas
*/
const CACHE_NAME = 'floodops-v0.4.0-texas';
const OFFLINE_URL = '/static/offline.html';
const CORE_ASSETS = [
  '/',
  '/static/index.html',
  '/static/manifest.json',
  '/health',
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

// IndexedDB for browser-local offline action drafts. Drafts are never executed
// by the service worker; an authenticated operator must review them after reconnecting.
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

async function queueOfflineActionDraft(incident_id, action) {
  try {
    const db = await openDB();
    const tx = db.transaction(STORE_NAME, 'readwrite');
    tx.objectStore(STORE_NAME).put({
      incident_id,
      action,
      queued_at: new Date().toISOString(),
      status: 'requires_reconfirmation'
    });
    console.log('[FloodOps SW] Saved offline action draft', action, incident_id);
  } catch (e) {
    console.warn('[FloodOps SW] Queue failed', e);
  }
}

self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);

  // API requests - network first. Failed approve/reject requests become local
  // drafts only; the worker never replays a life-safety decision.
  if (url.pathname.startsWith('/api/')) {
    // For approve/reject, queue if offline
    if ((url.pathname.includes('/approve') || url.pathname.includes('/reject')) && event.request.method === 'POST') {
      event.respondWith(
        fetch(event.request.clone()).catch(async () => {
          // Offline - preserve intent without changing server state.
          const incident_id = url.pathname.split('/')[3] || 'unknown';
          const action = url.pathname.includes('/approve') ? 'approve' : 'reject';
          await queueOfflineActionDraft(incident_id, action);
          return new Response(JSON.stringify({
            status: 'drafted_offline',
            incident_id,
            detail: 'Offline action saved as a browser-local draft. Reconnect, review current evidence, authenticate, and confirm again.',
            requires_reconfirmation: true,
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
          // Cache only explicitly public heartbeat state. Never cache an
          // authenticated API response or operator/incident records.
          const mayCache = event.request.method === 'GET'
            && resp.ok
            && !event.request.headers.has('Authorization')
            && url.pathname === '/api/heartbeat';
          if (mayCache) {
            const clone = resp.clone();
            caches.open(CACHE_NAME).then(cache => cache.put(event.request, clone));
          }
          return resp;
        })
        .catch(() => {
          const mayUseCache = event.request.method === 'GET'
            && !event.request.headers.has('Authorization')
            && url.pathname === '/api/heartbeat';
          return (mayUseCache ? caches.match(event.request) : Promise.resolve(null)).then(cached => {
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

console.log('[FloodOps SW] Loaded - Austin FloodOps interoperability prototype');
