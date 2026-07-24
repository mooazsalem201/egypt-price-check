"use client";

import { useCallback, useSyncExternalStore } from "react";

/**
 * A string preference backed by localStorage.
 *
 * Uses `useSyncExternalStore` rather than reading localStorage inside an effect: the
 * effect approach renders once with the default and again with the stored value, which
 * makes the zone buttons visibly flip after load. This reads the stored value during
 * render on the client while still giving the static export a stable server snapshot.
 */
export function usePersisted<T extends string>(
  key: string,
  fallback: T,
  isValid: (value: string) => boolean,
): [T, (value: T) => void] {
  const subscribe = useCallback((onChange: () => void) => {
    // "storage" only fires in *other* tabs, so same-tab writes dispatch their own event.
    window.addEventListener("storage", onChange);
    window.addEventListener(EVENT, onChange);
    return () => {
      window.removeEventListener("storage", onChange);
      window.removeEventListener(EVENT, onChange);
    };
  }, []);

  const getSnapshot = useCallback((): T => {
    try {
      const stored = localStorage.getItem(key);
      return stored && isValid(stored) ? (stored as T) : fallback;
    } catch {
      return fallback; // private browsing, storage disabled
    }
  }, [key, fallback, isValid]);

  const value = useSyncExternalStore(subscribe, getSnapshot, () => fallback);

  const setValue = useCallback(
    (next: T) => {
      try {
        localStorage.setItem(key, next);
      } catch {
        // Preference simply will not persist; the UI still updates.
      }
      window.dispatchEvent(new Event(EVENT));
    },
    [key],
  );

  return [value, setValue];
}

const EVENT = "persisted-change";
