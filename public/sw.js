/**
 * Offline-first service worker.
 *
 * Cell service is unreliable at the pyramids and along the North Coast, which is exactly
 * where the app is needed. Every same-origin asset is cached on first visit and served
 * from cache thereafter, so a dropped signal never blocks a price check.
 *
 * Live currency rates are deliberately NOT cached here -- lib/currency.ts owns their
 * freshness via localStorage, and a stale rate cached at the SW layer would be invisible.
 */

const CACHE = "egypt-prices-v1";

self.addEventListener("install", (event) => {
  // Take over immediately rather than waiting for every tab to close.
  event.waitUntil(caches.open(CACHE).then((cache) => cache.add("/")));
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim()),
  );
});

self.addEventListener("fetch", (event) => {
  const { request } = event;
  if (request.method !== "GET") return;

  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return; // let rate lookups hit the network

  event.respondWith(
    caches.match(request).then((cached) => {
      // Serve cache first for instant loads on bad 4G, then refresh in the background.
      const network = fetch(request)
        .then((response) => {
          if (response.ok) {
            const copy = response.clone();
            caches.open(CACHE).then((cache) => cache.put(request, copy));
          }
          return response;
        })
        .catch(() => cached ?? caches.match("/"));

      return cached ?? network;
    }),
  );
});
