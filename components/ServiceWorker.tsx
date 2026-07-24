"use client";

import { useEffect } from "react";

/** Registers the offline service worker. Failure is non-fatal -- the app still works online. */
export default function ServiceWorker() {
  useEffect(() => {
    if (!("serviceWorker" in navigator)) return;
    navigator.serviceWorker.register("/sw.js").catch(() => {
      // Unsupported browser or blocked by settings; nothing to do.
    });
  }, []);

  return null;
}
