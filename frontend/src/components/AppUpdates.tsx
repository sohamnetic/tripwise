import { useEffect, useState } from "react";
import { useRegisterSW } from "virtual:pwa-register/react";

const CHECK_EVERY_MS = 60 * 60 * 1000; // an installed app can stay open for days

/** Registers the offline worker, and tells the traveller when a new version is ready or when
 *  they're offline. */
export default function AppUpdates() {
  const {
    needRefresh: [needRefresh, setNeedRefresh],
    offlineReady: [offlineReady, setOfflineReady],
    updateServiceWorker,
  } = useRegisterSW({
    onRegisteredSW(_url, registration) {
      if (registration) setInterval(() => registration.update().catch(() => {}), CHECK_EVERY_MS);
    },
  });
  const online = useOnline();

  // "Ready to work offline" is good news once; don't keep it on screen.
  useEffect(() => {
    if (!offlineReady) return;
    const t = setTimeout(() => setOfflineReady(false), 5000);
    return () => clearTimeout(t);
  }, [offlineReady, setOfflineReady]);

  return (
    <div className="no-print pointer-events-none fixed inset-x-3 top-16 z-[2500] flex flex-col items-center gap-2" aria-live="polite">
      {!online && (
        <div className="fade-up pointer-events-auto rounded-full bg-ink px-4 py-2 text-sm font-semibold text-white shadow-lg">
          📴 You're offline. Trips you've opened before still work.
        </div>
      )}
      {needRefresh && (
        <div className="fade-up pointer-events-auto flex items-center gap-3 rounded-2xl bg-white p-2 pl-4 text-sm shadow-xl ring-1 ring-line">
          <span className="font-semibold">✨ A new version of Tripwise is ready</span>
          <button className="btn-primary px-3 py-1.5 text-xs" onClick={() => updateServiceWorker(true)}>Refresh</button>
          <button className="grid h-7 w-7 place-items-center rounded-full text-muted hover:bg-paper" onClick={() => setNeedRefresh(false)} aria-label="Later">×</button>
        </div>
      )}
      {offlineReady && !needRefresh && (
        <div className="fade-up pointer-events-auto rounded-full bg-sea-600 px-4 py-2 text-sm font-semibold text-white shadow-lg">
          ✓ Tripwise now works offline for trips you open
        </div>
      )}
    </div>
  );
}

function useOnline(): boolean {
  const [online, setOnline] = useState(() => navigator.onLine);
  useEffect(() => {
    const up = () => setOnline(true);
    const down = () => setOnline(false);
    window.addEventListener("online", up);
    window.addEventListener("offline", down);
    return () => {
      window.removeEventListener("online", up);
      window.removeEventListener("offline", down);
    };
  }, []);
  return online;
}
