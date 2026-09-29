import { Link } from "react-router-dom";
import Reveal from "../components/Reveal";
import Scene from "../components/Scene";
import { EXPLORE, LOOKS, destinationsWith, vibeFor } from "../lib/vibes";

// Every destination we know, with its scene, grouped by vibe.
export default function Destinations() {
  return (
    <div className="mx-auto max-w-6xl px-4 pb-10 pt-10">
      <p className="text-xs font-bold uppercase tracking-[0.2em] text-sea-700">All destinations</p>
      <h1 className="mt-2 text-3xl font-extrabold tracking-tight md:text-5xl">{Object.keys(LOOKS).length} places, one budget away</h1>
      <p className="mt-2 max-w-xl text-muted">Tap any destination to start planning. Places can appear in more than one group.</p>
      <div className="mt-5 flex flex-wrap gap-2">
        {EXPLORE.map((e) => (
          <a key={e.tag} href={`#${e.tag}`} className="chip border-line bg-white/80 text-ink hover:border-sea-500">{e.label}</a>
        ))}
      </div>

      {EXPLORE.map((e) => (
        <section key={e.tag} id={e.tag} className="scroll-mt-20 pt-10">
          <h2 className="text-xl font-extrabold md:text-2xl">{e.label}</h2>
          <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
            {destinationsWith(e.tag).map((city) => {
              const v = vibeFor(city);
              return (
                <Reveal key={city}>
                  <Link to="/" state={{ destination: city }} className="card lift group block overflow-hidden">
                    <div className="relative h-28 overflow-hidden md:h-32">
                      <Scene spec={v.spec} still className="transition-transform duration-700 group-hover:scale-105" />
                    </div>
                    <div className="p-3">
                      <div className="truncate font-bold">{v.emoji} {city}</div>
                      <div className="truncate text-xs text-muted">{v.tagline}</div>
                    </div>
                  </Link>
                </Reveal>
              );
            })}
          </div>
        </section>
      ))}
    </div>
  );
}
