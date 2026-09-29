import { Link, Outlet } from "react-router-dom";
import Footer from "./Footer";

export default function Layout() {
  return (
    <div className="relative flex min-h-screen flex-col overflow-x-clip">
      {/* page-wide texture and soft colour so no area reads as a flat grey block */}
      <div className="bg-dots mask-fade-y pointer-events-none absolute inset-0 -z-10 opacity-70" />
      <div className="blob -z-10 left-[-120px] top-[700px] h-[380px] w-[380px] bg-sea-100" />
      <div className="blob -z-10 right-[-140px] top-[1200px] h-[420px] w-[420px] bg-sand-100" />

      <header className="no-print sticky top-0 z-[1000] border-b border-line/70 bg-white/80 backdrop-blur">
        <div className="mx-auto flex h-14 max-w-6xl items-center justify-between px-4">
          <Link to="/" className="flex items-center gap-2 text-lg font-extrabold tracking-tight text-sea-900">
            <span className="grid h-8 w-8 place-items-center rounded-lg bg-sea-600 text-white">🧭</span>
            Tripwise
          </Link>
          <nav className="flex items-center gap-1">
            <Link to="/destinations" className="rounded-full px-3 py-1.5 text-sm font-semibold text-ink/70 hover:bg-paper hover:text-ink">
              Destinations
            </Link>
            <Link to="/" className="rounded-full bg-sea-50 px-3 py-1.5 text-sm font-semibold text-sea-700 ring-1 ring-sea-100 hover:bg-sea-100">
              Plan a trip
            </Link>
          </nav>
        </div>
      </header>
      <main className="flex-1">
        <Outlet />
      </main>
      <Footer />
    </div>
  );
}
