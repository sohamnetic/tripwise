// Renders the app icons from public/logo.svg (rounded, for browsers and the install prompt) and
// public/logo-full.svg (edge to edge: Android masks it to its own shape, iOS rounds the corners).
// Run after changing either SVG: node scripts/make-icons.mjs
import { readFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import sharp from "sharp";

const out = (name) => fileURLToPath(new URL(`../public/${name}`, import.meta.url));
const rounded = await readFile(out("logo.svg"));
const full = await readFile(out("logo-full.svg"));

const jobs = [
  [rounded, 64, "pwa-64x64.png"],
  [rounded, 192, "pwa-192x192.png"],
  [rounded, 512, "pwa-512x512.png"],
  [full, 512, "maskable-icon-512x512.png"],
  [full, 180, "apple-touch-icon-180x180.png"],
  [rounded, 32, "favicon-32x32.png"],
];
for (const [svg, size, name] of jobs) {
  await sharp(svg, { density: 384 }).resize(size, size).png({ compressionLevel: 9 }).toFile(out(name));
  console.log("wrote", name);
}
