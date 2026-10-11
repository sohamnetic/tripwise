import { useEffect, useRef, useState, type FormEvent, type ReactNode } from "react";
import { createPortal } from "react-dom";
import { useNavigate } from "react-router-dom";
import { api, useHealth } from "../api/client";
import type { ChatTurn, Rating, Suggestion, TripRequest } from "../api/types";
import { rupees } from "../lib/format";
import { loadLast } from "../lib/lastRequest";
import { vibeFor } from "../lib/vibes";

// "Ask Tripwise": a chat that suggests where to go and when, within a budget. The 💬 button lives in
// the bottom notice stack (Layout); the panel opens over the page (full screen on phones).

interface Message extends ChatTurn {
  suggestions?: Suggestion[];
  mode?: "ai" | "simple";
  failed?: boolean; // an error shown to the traveller, not part of the conversation
}

const STORE_KEY = "tripwise:chat";
const MAX_CHARS = 600;
const STARTERS = [
  "Where can I go in December under ₹30k?",
  "Somewhere cool in May for 2 from Kolkata",
  "Beach trip for 4 from Delhi",
  "Long weekend from Bengaluru",
];
const GREETING = "Hi! Tell me **when** you'd like to travel and roughly your **budget**, and I'll suggest places that are good then. Your home city helps too.";

const RATING_STYLE: Record<Rating, string> = {
  Great: "bg-sea-600 text-white",
  Good: "bg-sea-50 text-sea-700 ring-1 ring-sea-100",
  Okay: "bg-sand-100 text-sand-600",
  Avoid: "bg-red-50 text-red-700",
  Closed: "bg-red-50 text-red-700",
};

function loadChat(): Message[] {
  try {
    const list = JSON.parse(sessionStorage.getItem(STORE_KEY) ?? "[]");
    return Array.isArray(list) ? list : [];
  } catch {
    return [];
  }
}

function saveChat(messages: Message[]) {
  try {
    sessionStorage.setItem(STORE_KEY, JSON.stringify(messages.slice(-30)));
  } catch {
    /* storage blocked: the chat just won't survive a reload */
  }
}

/** Just enough formatting for chat replies (bold, lists, paragraphs), without rendering any HTML. */
function Formatted({ text }: { text: string }) {
  const inline = (line: string): ReactNode[] =>
    line.split(/(\*\*[^*]+\*\*)/g).map((part, i) =>
      part.startsWith("**") && part.endsWith("**") ? <strong key={i}>{part.slice(2, -2)}</strong> : part);
  const blocks: ReactNode[] = [];
  let list: string[] = [];
  const flush = () => {
    if (list.length) blocks.push(<ul key={`l${blocks.length}`} className="my-1.5 list-disc space-y-1 pl-5">{list.map((l, i) => <li key={i}>{inline(l)}</li>)}</ul>);
    list = [];
  };
  for (const raw of text.split("\n")) {
    const line = raw.trim();
    const item = line.match(/^(?:[-*•]|\d+[.)])\s+(.*)$/);
    if (item) {
      list.push(item[1]);
      continue;
    }
    flush();
    if (line) blocks.push(<p key={`p${blocks.length}`} className="my-1">{inline(line.replace(/^#+\s*/, ""))}</p>);
  }
  flush();
  return <>{blocks}</>;
}

function SuggestionCard({ s, onPlan }: { s: Suggestion; onPlan: (s: Suggestion) => void }) {
  const vibe = vibeFor(s.name);
  const c = s.cost;
  return (
    <div className="rounded-2xl bg-white p-3 ring-1 ring-line">
      <div className="flex items-start gap-3">
        <span className="grid h-11 w-11 shrink-0 place-items-center rounded-xl bg-paper text-2xl">{vibe.emoji}</span>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
            <span className="font-bold">{s.name}</span>
            <span className={`rounded-full px-2 py-0.5 text-[11px] font-bold ${RATING_STYLE[s.season.rating]}`}>{s.season.rating}</span>
          </div>
          <div className="truncate text-xs text-muted">{s.tagline}</div>
        </div>
      </div>
      <div className="mt-2 space-y-1 text-[13px]">
        <div>🌤️ {s.season.weather}</div>
        {s.season.rating !== "Great" && <div className="text-muted">{s.season.reason}</div>}
        {s.season.note && <div className="text-sand-600">⚠️ {s.season.note}</div>}
        <div className="flex flex-wrap items-center gap-x-2">
          <span className="font-semibold">💰 {rupees(c.low)}–{rupees(c.high)}</span>
          <span className="text-muted">for {c.travellers}, {c.nights} night{c.nights > 1 ? "s" : ""}{c.includes_travel ? "" : ", plus travel"}</span>
        </div>
        {c.fits_budget === true && <div className="font-semibold text-sea-700">✓ Fits your budget</div>}
        {c.fits_budget === false && <div className="font-semibold text-sand-600">About {rupees(c.over_by)} over your budget</div>}
        {c.transport_label && <div className="text-xs text-muted">{c.transport_label}</div>}
      </div>
      <button className="btn-primary mt-2.5 w-full py-2 text-sm" onClick={() => onPlan(s)}>Plan this trip →</button>
    </div>
  );
}

function useIsPhone() {
  const query = "(max-width: 639px)"; // Tailwind's sm breakpoint: full-screen panel below it
  const [phone, setPhone] = useState(() => window.matchMedia(query).matches);
  useEffect(() => {
    const mq = window.matchMedia(query);
    const update = () => setPhone(mq.matches);
    mq.addEventListener("change", update);
    return () => mq.removeEventListener("change", update);
  }, []);
  return phone;
}

function useVisualHeight(active: boolean) {
  // Phones: size the panel to the part of the screen the keyboard leaves visible.
  const [height, setHeight] = useState<number | null>(null);
  useEffect(() => {
    const vv = window.visualViewport;
    if (!active || !vv) return;
    const update = () => setHeight(vv.height);
    update();
    vv.addEventListener("resize", update);
    return () => vv.removeEventListener("resize", update);
  }, [active]);
  return active ? height : null; // e.g. a tablet rotated to landscape goes back to the card size
}

export default function ChatWidget() {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>(loadChat);
  const [text, setText] = useState("");
  const [sending, setSending] = useState(false);
  const navigate = useNavigate();
  const health = useHealth();
  const inputRef = useRef<HTMLInputElement>(null);
  const endRef = useRef<HTMLDivElement>(null);
  const buttonRef = useRef<HTMLButtonElement>(null);
  const phone = useIsPhone();
  const visualHeight = useVisualHeight(open && phone);

  useEffect(() => {
    saveChat(messages);
  }, [messages]);
  useEffect(() => {
    // braces matter: newer Chrome returns a Promise from scrollIntoView, and React would treat a
    // returned value as the effect's clean-up function
    endRef.current?.scrollIntoView({ block: "end" });
  }, [messages, sending, open]);
  useEffect(() => {
    if (!open) return;
    if (!phone) inputRef.current?.focus(); // on phones, don't pop the keyboard over the greeting
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && close();
    window.addEventListener("keydown", onKey);
    document.body.style.overflow = phone ? "hidden" : "";
    return () => {
      window.removeEventListener("keydown", onKey);
      document.body.style.overflow = "";
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, phone]);

  const close = () => {
    setOpen(false);
    buttonRef.current?.focus();
  };

  const send = async (raw: string) => {
    const message = raw.trim().slice(0, MAX_CHARS);
    if (!message || sending) return;
    const history: Message[] = [...messages, { role: "user", text: message }];
    setMessages(history);
    setText("");
    setSending(true);
    try {
      const turns = history.filter((m) => !m.failed).map(({ role, text }) => ({ role, text }));
      const reply = await api.chat(turns);
      setMessages((m) => [...m, { role: "assistant", text: reply.reply, suggestions: reply.suggestions, mode: reply.mode }]);
    } catch (e) {
      setMessages((m) => [...m, { role: "assistant", text: (e as Error).message, failed: true }]);
    } finally {
      setSending(false);
    }
  };

  const plan = (s: Suggestion) => {
    const last = loadLast();
    const p = s.prefill;
    const request: TripRequest = {
      origin: p.origin ?? last?.origin ?? "", destination: p.destination, start_date: p.start_date, end_date: p.end_date,
      travellers: p.travellers, budget: p.budget, style: p.style,
      interests: p.interests.length ? p.interests : last?.interests ?? [], transport: last?.transport ?? "any",
    };
    setOpen(false);
    navigate("/", { state: { request } });
  };

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    void send(text);
  };

  const ai = health.data?.chat_ai !== false;
  const lastMode = [...messages].reverse().find((m) => m.mode)?.mode;

  const panel = open && createPortal(
    <div className="fixed inset-0 z-[2600] sm:inset-auto sm:bottom-4 sm:right-4" role="dialog" aria-modal="true" aria-label="Ask Tripwise">
      <div className="fade-up flex h-[100dvh] flex-col bg-paper sm:h-[min(640px,calc(100vh-2rem))] sm:w-[400px] sm:overflow-hidden sm:rounded-3xl sm:shadow-2xl sm:ring-1 sm:ring-line"
        style={visualHeight ? { height: visualHeight } : undefined}>
        <header className="flex items-center gap-3 border-b border-line bg-white px-4 py-3">
          <img src="/logo.svg" alt="" className="h-9 w-9 rounded-xl" />
          <div className="min-w-0 flex-1">
            <div className="font-extrabold leading-tight">Ask Tripwise</div>
            <div className="truncate text-xs text-muted">Where & when to go, for your budget</div>
          </div>
          {messages.length > 0 && (
            <button className="rounded-full px-2.5 py-1.5 text-xs font-semibold text-muted hover:bg-paper hover:text-ink"
              onClick={() => setMessages([])} disabled={sending}>New chat</button>
          )}
          <button className="grid h-9 w-9 place-items-center rounded-full text-xl text-muted hover:bg-paper hover:text-ink" onClick={close} aria-label="Close chat">×</button>
        </header>

        <div className="flex-1 space-y-3 overflow-y-auto overscroll-contain px-3 py-4" aria-live="polite">
          <Bubble role="assistant"><Formatted text={GREETING} /></Bubble>
          {messages.length === 0 && (
            <div className="flex flex-wrap gap-2 pl-1">
              {STARTERS.map((s) => (
                <button key={s} className="rounded-full bg-white px-3 py-1.5 text-left text-[13px] font-medium text-sea-700 ring-1 ring-sea-100 hover:bg-sea-50"
                  onClick={() => void send(s)}>{s}</button>
              ))}
            </div>
          )}
          {messages.map((m, i) => (
            <div key={i} className="space-y-2">
              <Bubble role={m.role} failed={m.failed}>{m.role === "user" ? m.text : <Formatted text={m.text} />}</Bubble>
              {m.suggestions && m.suggestions.length > 0 && (
                <div className="space-y-2 pl-1">
                  {m.suggestions.map((s) => <SuggestionCard key={s.name} s={s} onPlan={plan} />)}
                </div>
              )}
            </div>
          ))}
          {sending && (
            <Bubble role="assistant">
              <span className="inline-flex gap-1 py-1" aria-label="Tripwise is typing">
                {[0, 1, 2].map((i) => <span key={i} className="h-2 w-2 animate-bounce rounded-full bg-muted" style={{ animationDelay: `${i * 0.15}s` }} />)}
              </span>
            </Bubble>
          )}
          <div ref={endRef} />
        </div>

        <form onSubmit={onSubmit} className="border-t border-line bg-white px-3 pb-[max(0.75rem,env(safe-area-inset-bottom))] pt-3">
          <div className="flex items-center gap-2">
            <label htmlFor="chat-input" className="sr-only">Message</label>
            <input id="chat-input" ref={inputRef} value={text} onChange={(e) => setText(e.target.value)} maxLength={MAX_CHARS}
              placeholder="e.g. Hills in June under ₹40k" autoComplete="off" enterKeyHint="send"
              className="input flex-1 rounded-full" disabled={!navigator.onLine} />
            <button type="submit" className="btn-primary grid h-11 w-11 shrink-0 place-items-center rounded-full p-0" disabled={!text.trim() || sending} aria-label="Send">
              <svg viewBox="0 0 24 24" className="h-5 w-5" fill="currentColor" aria-hidden="true"><path d="M3.4 20.4 21 12 3.4 3.6l.1 6.5L15 12 3.5 13.9z" /></svg>
            </button>
          </div>
          <p className="mt-2 text-[11px] leading-snug text-muted">
            {!ai || lastMode === "simple"
              ? "Simple mode: answers come from Tripwise's own season and price data. Costs are rough; the planner gives exact prices."
              : "Chats are handled by Google Gemini and may be used to improve Google's models. Don't share personal details. Costs are rough; the planner gives exact prices."}
          </p>
        </form>
      </div>
    </div>,
    document.body,
  );

  return (
    <>
      {!open && (
        <div className="flex justify-end">
          <button ref={buttonRef} onClick={() => setOpen(true)} aria-label="Ask Tripwise: where and when to go"
            className="pointer-events-auto flex h-14 items-center gap-2 rounded-full bg-sea-600 pl-4 pr-5 font-bold text-white shadow-xl shadow-sea-600/30 transition hover:bg-sea-700">
            <span className="text-xl" aria-hidden="true">💬</span>
            <span className="text-sm">Ask Tripwise</span>
          </button>
        </div>
      )}
      {panel}
    </>
  );
}

function Bubble({ role, failed, children }: { role: "user" | "assistant"; failed?: boolean; children: ReactNode }) {
  const mine = role === "user";
  return (
    <div className={`flex ${mine ? "justify-end" : "justify-start"}`}>
      <div className={`max-w-[85%] rounded-2xl px-3.5 py-2 text-[14px] leading-relaxed ${
        mine ? "rounded-br-md bg-sea-600 text-white" : failed ? "rounded-bl-md bg-red-50 text-red-700 ring-1 ring-red-100" : "rounded-bl-md bg-white text-ink ring-1 ring-line"}`}>
        {children}
      </div>
    </div>
  );
}
