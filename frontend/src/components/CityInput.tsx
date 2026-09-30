import { useEffect, useId, useMemo, useRef, useState, type KeyboardEvent, type ReactNode } from "react";
import { useAllCities, useCities } from "../api/client";
import type { CityOption } from "../api/types";
import { vibeFor } from "../lib/vibes";

interface Props {
  label: string;
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  /** Shown before anything is typed, in this order. */
  popular: string[];
  popularLabel: string;
  /** Destinations also show their one-line vibe ("Sun, sand & susegād"). */
  showTagline?: boolean;
}

const LIMIT = 8;

interface Match {
  city: CityOption;
  alias?: string; // matched by another name: "Bombay" → Mumbai
}

/** Cities whose name (or another name) starts with the text first, then ones containing it.
 *  Within each group, `popular` cities come first ("ma" → Manali before Mahabalipuram). */
export function matchCities(all: CityOption[], text: string, popular: string[] = []): Match[] {
  const rank = (c: CityOption) => (popular.includes(c.name) ? popular.indexOf(c.name) : popular.length);
  all = [...all].sort((a, b) => rank(a) - rank(b));
  const q = text.trim().toLowerCase();
  const tiers: Match[][] = [[], [], [], []];
  for (const city of all) {
    const name = city.name.toLowerCase();
    const alias = city.aliases.find((a) => a.startsWith(q));
    if (name.startsWith(q)) tiers[0].push({ city });
    else if (alias) tiers[1].push({ city, alias });
    else if (name.split(/[\s-]+/).some((w) => w.startsWith(q))) tiers[2].push({ city }); // "island" → Havelock Island
    else if (name.includes(q) || city.aliases.some((a) => a.includes(q)))
      tiers[3].push({ city, alias: name.includes(q) ? undefined : city.aliases.find((a) => a.includes(q)) });
  }
  return tiers.flat().slice(0, LIMIT);
}

/** The typed part of the name in bold teal: "Go" → **Go**a. */
function Highlight({ name, text }: { name: string; text: string }): ReactNode {
  const i = text ? name.toLowerCase().indexOf(text.trim().toLowerCase()) : -1;
  if (i < 0) return name;
  const n = text.trim().length;
  return (
    <>
      {name.slice(0, i)}
      <mark className="bg-transparent font-extrabold text-sea-700">{name.slice(i, i + n)}</mark>
      {name.slice(i + n)}
    </>
  );
}

const titleCase = (s: string) => s.replace(/\b\w/g, (c) => c.toUpperCase());
const isTouch = () => window.matchMedia("(pointer: coarse)").matches;

// A search box with Tripwise's own suggestion list: the browser's built-in one looks different
// on every phone and often doesn't update while you type.
export default function CityInput({ label, value, onChange, placeholder, popular, popularLabel, showTagline }: Props) {
  const id = useId();
  const listId = `${id}-list`;
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLUListElement>(null);
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);
  const closeTimer = useRef<number | undefined>(undefined);
  useEffect(() => () => window.clearTimeout(closeTimer.current), []);

  const all = useAllCities();
  // If the full list can't load (e.g. an older backend), ask the server as you type instead.
  const serverSearch = useCities(all.isError ? value : "", all.isError);

  const exact = all.data?.find((c) => c.name.toLowerCase() === value.trim().toLowerCase());
  const typing = value.trim() !== "" && !exact;
  const items: Match[] = useMemo(() => {
    if (all.data) {
      if (typing) return matchCities(all.data, value, popular);
      const byName = new Map(all.data.map((c) => [c.name, c]));
      return popular.flatMap((n) => (byName.has(n) ? [{ city: byName.get(n)! }] : []));
    }
    return (serverSearch.data ?? []).map((c) => ({ city: { ...c, aliases: [] } }));
  }, [all.data, serverSearch.data, typing, value, popular]);

  useEffect(() => setActive(0), [value]);
  useEffect(() => {
    listRef.current?.querySelector(`[data-index="${active}"]`)?.scrollIntoView({ block: "nearest" });
  }, [active]);

  const choose = (m: Match) => {
    onChange(m.city.name);
    setOpen(false);
    if (isTouch()) inputRef.current?.blur(); // put the keyboard away once a city is picked
  };

  const onKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "ArrowDown" || e.key === "ArrowUp") {
      e.preventDefault();
      if (!open) return setOpen(true);
      const step = e.key === "ArrowDown" ? 1 : -1;
      setActive((a) => (a + step + items.length) % Math.max(items.length, 1));
    } else if (e.key === "Enter" && open && items[active]) {
      e.preventDefault(); // pick the city rather than submitting the form
      choose(items[active]);
    } else if (e.key === "Escape" && open) {
      e.preventDefault();
      setOpen(false);
    }
  };

  const onFocus = () => {
    window.clearTimeout(closeTimer.current);
    setOpen(true);
    inputRef.current?.select(); // typing replaces the current city
    if (isTouch()) {
      // on phones the keyboard covers the bottom half; lift the box so the list has room
      setTimeout(() => {
        // just below the sticky header, with the box's label still in view
        const top = (inputRef.current?.getBoundingClientRect().top ?? 0) + window.scrollY - 112;
        window.scrollTo({ top, behavior: "smooth" });
      }, 250);
    }
  };

  const showList = open && (items.length > 0 || typing);
  const current = exact ?? (all.data ? undefined : { name: value });

  return (
    <div className="relative">
      <label htmlFor={id} className="label">{label}</label>
      <div className="relative">
        <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-lg" aria-hidden="true">
          {current && value ? vibeFor(current.name).emoji : (
            <svg viewBox="0 0 24 24" className="h-5 w-5 text-muted" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="11" cy="11" r="7" /><path d="m20 20-3.5-3.5" strokeLinecap="round" />
            </svg>
          )}
        </span>
        <input
          ref={inputRef}
          id={id}
          className="input pl-11 pr-10"
          role="combobox"
          aria-autocomplete="list"
          aria-expanded={showList}
          aria-controls={listId}
          aria-activedescendant={showList && items[active] ? `${id}-opt-${active}` : undefined}
          value={value}
          placeholder={placeholder}
          autoComplete="off"
          autoCorrect="off"
          autoCapitalize="words"
          spellCheck={false}
          enterKeyHint="next"
          onChange={(e) => { onChange(e.target.value); setOpen(true); }}
          onFocus={onFocus}
          // close a moment later: on some phones the box blurs just before a tap on a suggestion lands
          onBlur={() => { closeTimer.current = window.setTimeout(() => setOpen(false), 150); }}
          onKeyDown={onKeyDown}
          required
        />
        {value && (
          <button type="button" aria-label={`Clear ${label.toLowerCase()}`}
            className="absolute right-1.5 top-1/2 grid h-8 w-8 -translate-y-1/2 place-items-center rounded-full text-lg text-muted hover:bg-paper hover:text-ink"
            onMouseDown={(e) => e.preventDefault()} // keep focus in the box
            onClick={() => { onChange(""); setOpen(true); inputRef.current?.focus(); }}>
            ×
          </button>
        )}
      </div>

      {showList && (
        <ul ref={listRef} id={listId} role="listbox" aria-label={`${label} suggestions`}
          className="fade-up absolute inset-x-0 top-full z-30 mt-1.5 max-h-[min(22rem,55vh)] overflow-y-auto overscroll-contain rounded-2xl bg-white p-1.5 shadow-xl shadow-slate-900/10 ring-1 ring-line">
          {!typing && items.length > 0 && (
            <li role="presentation" className="px-2.5 pb-1 pt-1 text-[11px] font-bold uppercase tracking-wide text-muted">{popularLabel}</li>
          )}
          {items.map((m, i) => {
            const vibe = vibeFor(m.city.name);
            const selected = m.city.name === exact?.name;
            return (
              <li key={m.city.name} id={`${id}-opt-${i}`} data-index={i} role="option" aria-selected={i === active}
                onMouseDown={(e) => e.preventDefault()} // so the box doesn't lose focus before the tap lands
                onMouseMove={() => i !== active && setActive(i)}
                onClick={() => choose(m)}
                className={`flex cursor-pointer items-center gap-3 rounded-xl px-2.5 py-2 transition-colors ${i === active ? "bg-sea-50" : ""}`}>
                <span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-paper text-xl">{vibe.emoji}</span>
                <span className="min-w-0 flex-1">
                  <span className="block truncate font-semibold text-ink"><Highlight name={m.city.name} text={typing ? value : ""} /></span>
                  <span className="block truncate text-xs text-muted">
                    {m.alias ? <>also <b className="font-semibold text-ink/70">{titleCase(m.alias)}</b> · </> : null}
                    {showTagline ? vibe.tagline : `${m.city.state}, ${m.city.country}`}
                  </span>
                </span>
                {selected && <span className="shrink-0 text-sea-600" aria-hidden="true">✓</span>}
              </li>
            );
          })}
          {typing && items.length === 0 && (
            <li role="presentation" className="px-3 py-3 text-sm text-muted">
              No city called “{value.trim()}” yet. Try the nearest big city.
            </li>
          )}
        </ul>
      )}
    </div>
  );
}
