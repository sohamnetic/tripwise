// Renders every destination scene into one static HTML page, for reviewing the artwork.
// Usage (from frontend/):
//   npx esbuild scripts/contact-sheet.tsx --bundle --platform=node --outfile=scripts/.contact-sheet.cjs --jsx=automatic --log-level=warning
//   node scripts/.contact-sheet.cjs > contact-sheet.html
import { renderToStaticMarkup } from "react-dom/server";
import Scene from "../src/components/Scene";
import { LOOKS, vibeFor } from "../src/lib/vibes";

// Optional: `node … large goa jaipur` renders just those, at hero size, one per row.
const [mode, ...picked] = process.argv.slice(2);
const large = mode === "large";
const keys = large ? picked : Object.keys(LOOKS);

// One render root, so every scene's gradient ids are unique (as they are in the app).
const cards = renderToStaticMarkup(
  <>
    {keys.map((key) => {
      const v = vibeFor(key);
      return (
        <figure key={key}>
          <div className="scene"><Scene spec={v.spec} /></div>
          <figcaption>{v.emoji} {key.replace(/\b\w/g, (c) => c.toUpperCase())}</figcaption>
        </figure>
      );
    })}
  </>,
);

// Movers sit at x = 0 without their animation; park them mid-scene so they're visible.
process.stdout.write(`<!doctype html><meta charset="utf-8"><style>
body{margin:12px;font:13px system-ui;background:#fff}
main{display:grid;grid-template-columns:repeat(${large ? 1 : 4},1fr);gap:10px}
figure{margin:0}.scene{position:relative;height:${large ? 380 : 130}px;overflow:hidden;border-radius:8px}
.scene svg{position:absolute;inset:0;width:100%;height:100%}
figcaption{padding:3px 2px;font-weight:600}
.anim-cross{transform:translateX(520px)}.anim-cross-rev{transform:translateX(620px)}
.anim-glide{transform:translate(420px,20px)}.anim-cable{transform:translate(500px,-82px)}
.anim-ski{transform:translate(480px,40px)}.anim-fall{transform:translateY(160px)}
.anim-jump{transform:translate(40px,-30px)}
</style><main>${cards}</main>`);
