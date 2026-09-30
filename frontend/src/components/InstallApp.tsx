import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { useLocation } from "react-router-dom";
import { promptInstall, useInstall } from "../lib/pwa";

const DISMISS_KEY = "tripwise:install-dismissed";
const DISMISS_DAYS = 14;
const SHOW_AFTER_MS = 2500; // don't greet people with a popup the moment the page opens

function dismissedRecently(): boolean {
  try {
    const at = Number(localStorage.getItem(DISMISS_KEY) ?? 0);
    return Date.now() - at < DISMISS_DAYS * 24 * 60 * 60 * 1000;
  } catch {
    return false;
  }
}

function rememberDismissed() {
  try {
    localStorage.setItem(DISMISS_KEY, String(Date.now()));
  } catch {
    /* private mode: it'll just show again next time */
  }
}

/** Steps for iPhone/iPad, where Safari has no install button of its own. Rendered on top of the
 *  page (not inside whatever opened it), so it looks the same from the dark footer as anywhere. */
function IOSSteps({ onClose }: { onClose: () => void }) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return createPortal(
    <div className="fixed inset-0 z-[3000] flex items-end justify-center bg-ink/40 p-3 text-left text-ink backdrop-blur-sm sm:items-center"
      role="dialog" aria-modal="true" aria-labelledby="ios-install-title" onClick={onClose}>
      <div className="fade-up w-full max-w-sm rounded-3xl bg-white p-5 shadow-xl" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center gap-3">
          <img src="/apple-touch-icon-180x180.png" alt="" className="h-12 w-12 rounded-xl" />
          <div>
            <div id="ios-install-title" className="font-extrabold">Add Tripwise to your Home Screen</div>
            <div className="text-sm text-muted">It opens full screen, like an app.</div>
          </div>
        </div>
        <ol className="mt-4 space-y-3 text-sm">
          <li className="flex items-center gap-3">
            <span className="grid h-7 w-7 shrink-0 place-items-center rounded-full bg-sea-50 font-bold text-sea-700">1</span>
            <span>
              Tap the <b>Share</b> button{" "}
              <svg viewBox="0 0 24 24" className="inline h-5 w-5 align-text-bottom text-sea-700" fill="none" stroke="currentColor" strokeWidth="2" aria-label="Share icon">
                <path d="M12 3v12M8 7l4-4 4 4" strokeLinecap="round" strokeLinejoin="round" />
                <path d="M6 11H5a1 1 0 0 0-1 1v8a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-8a1 1 0 0 0-1-1h-1" strokeLinecap="round" />
              </svg>
              . In newer Safari it's inside the <b>☰</b> or <b>•••</b> menu next to the address bar.
            </span>
          </li>
          <li className="flex items-center gap-3">
            <span className="grid h-7 w-7 shrink-0 place-items-center rounded-full bg-sea-50 font-bold text-sea-700">2</span>
            <span>Tap <b>Add to Home Screen</b> (scroll down the list if you don't see it)</span>
          </li>
          <li className="flex items-center gap-3">
            <span className="grid h-7 w-7 shrink-0 place-items-center rounded-full bg-sea-50 font-bold text-sea-700">3</span>
            <span>Tap <b>Add</b>. Tripwise appears on your Home Screen.</span>
          </li>
        </ol>
        <button className="btn-primary mt-5 w-full" onClick={onClose}>Got it</button>
      </div>
    </div>,
    document.body,
  );
}

/** Starts installing: the browser's own dialog where there is one, else the iPhone steps. */
function useStartInstall() {
  const mode = useInstall();
  const [iosSteps, setIosSteps] = useState(false);
  const start = async () => {
    if (mode === "prompt") await promptInstall();
    else if (mode === "ios") setIosSteps(true);
  };
  const steps = iosSteps ? <IOSSteps onClose={() => setIosSteps(false)} /> : null;
  return { mode, start, steps };
}

/** A small card at the bottom of the screen offering to install, until installed or dismissed. */
export function InstallBanner() {
  const { mode, start, steps } = useStartInstall();
  const { pathname } = useLocation();
  const [ready, setReady] = useState(false);
  const [hidden, setHidden] = useState(dismissedRecently);

  useEffect(() => {
    const t = setTimeout(() => setReady(true), SHOW_AFTER_MS);
    return () => clearTimeout(t);
  }, []);

  const offer = (mode === "prompt" || mode === "ios") && ready && !hidden && !pathname.startsWith("/planning");
  const close = () => {
    rememberDismissed();
    setHidden(true);
  };

  return (
    <>
      {offer && (
        <div className="pointer-events-auto">
          <div className="fade-up flex items-center gap-3 rounded-2xl bg-white p-3 shadow-xl ring-1 ring-line" role="region" aria-label="Install Tripwise">
            <img src="/pwa-64x64.png" alt="" className="h-11 w-11 shrink-0 rounded-xl" />
            <div className="min-w-0 flex-1">
              <div className="text-sm font-bold">Get the Tripwise app</div>
              <div className="text-xs text-muted">Opens from your home screen. Trips you've opened work offline.</div>
            </div>
            <button className="btn-primary shrink-0 px-3.5 py-2 text-sm" onClick={start}>
              Install
            </button>
            <button className="grid h-8 w-8 shrink-0 place-items-center rounded-full text-lg text-muted hover:bg-paper" onClick={close} aria-label="Not now">
              ×
            </button>
          </div>
        </div>
      )}
      {steps}
    </>
  );
}

/** "Install the app" link for the footer; hidden where installing isn't possible or already done. */
export function InstallLink({ className = "" }: { className?: string }) {
  const { mode, start, steps } = useStartInstall();
  if (mode !== "prompt" && mode !== "ios") return steps;
  return (
    <>
      <button type="button" onClick={start} className={className}>📲 Install the app</button>
      {steps}
    </>
  );
}
