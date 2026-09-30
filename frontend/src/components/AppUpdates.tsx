import { useEffect, useState } from "react";
import { useRegisterSW } from "virtual:pwa-register/react";

const CHECK_EVERY_MS = 60 * 60 * 1000; // an installed app can stay open for days

/** Registers the offline worker, and tells the traveller when a new version is ready or when
 *  they're offline. */
export default function AppUpdates() {
  const {
    needRefresh: [needRefresh, setNeedRefresh],
    updateServiceWorker,
  } = useRegisterSW({
    onRegisteredSW(_url, registration) {
      if (registration) setInterval(() => registration.update().catch(() => {}), CHECK_EVERY_MS);
    },
  });
  const online = useOnline();

  return (
    <div className="flex flex-col gap-2" aria-live="polite">
      {!online && (
        <div className="fade-up pointer-events-auto rounded-2xl bg-ink px-4 py-3 text-sm font-semibold text-white shadow-lg">
          📴 You're offline. Trips you've opened before still work.
        </div>
      )}
      {needRefresh && (
        <div className="fade-up pointer-events-auto flex items-center gap-3 rounded-2xl bg-white p-3 pl-4 text-sm shadow-xl ring-1 ring-line">
          <span className="min-w-0 flex-1 font-semibold">✨ A new version of Tripwise is ready</span>
          <button className="btn-primary shrink-0 px-3.5 py-2 text-sm" onClick={() => updateServiceWorker(true)}>Refresh</button>
          <button className="grid h-8 w-8 shrink-0 place-items-center rounded-full text-lg text-muted hover:bg-paper" onClick={() => setNeedRefresh(false)} aria-label="Later">×</button>
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
