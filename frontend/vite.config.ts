import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";
import { VitePWA } from "vite-plugin-pwa";

const DAY = 24 * 60 * 60;

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
    // Makes the site installable as an app (home-screen icon, full screen, works offline for
    // trips you've opened). Icons come from scripts/make-icons.mjs.
    VitePWA({
      registerType: "prompt", // a new version waits until the traveller taps "Refresh"
      injectRegister: false, // registered from src/components/AppUpdates.tsx
      includeAssets: ["logo.svg", "favicon-32x32.png", "apple-touch-icon-180x180.png"],
      manifest: {
        id: "/",
        name: "Tripwise: budget trip planner",
        short_name: "Tripwise",
        description:
          "Enter where you're going and your budget. Get transport, a stay, a day-by-day plan and links to book it all, priced in ₹.",
        lang: "en-IN",
        start_url: "/",
        scope: "/",
        display: "standalone",
        background_color: "#f8fafc",
        theme_color: "#0d8573",
        categories: ["travel"],
        icons: [
          { src: "pwa-64x64.png", sizes: "64x64", type: "image/png" },
          { src: "pwa-192x192.png", sizes: "192x192", type: "image/png" },
          { src: "pwa-512x512.png", sizes: "512x512", type: "image/png" },
          { src: "maskable-icon-512x512.png", sizes: "512x512", type: "image/png", purpose: "maskable" },
        ],
        shortcuts: [
          { name: "Plan a trip", url: "/", icons: [{ src: "pwa-192x192.png", sizes: "192x192", type: "image/png" }] },
          { name: "Destinations", url: "/destinations", icons: [{ src: "pwa-192x192.png", sizes: "192x192", type: "image/png" }] },
        ],
      },
      workbox: {
        // The app itself: stored on the phone so it opens instantly and offline.
        globPatterns: ["**/*.{js,css,html,svg,png,woff2}"],
        navigateFallback: "/index.html",
        navigateFallbackDenylist: [/^\/api\//],
        cleanupOutdatedCaches: true,
        runtimeCaching: [
          {
            // Trips you've opened: fresh from the server when online, the saved copy when offline.
            urlPattern: ({ url, request }) => request.method === "GET" && /\/api\/trips\/[^/]+$/.test(url.pathname),
            handler: "NetworkFirst",
            options: {
              cacheName: "trips",
              networkTimeoutSeconds: 10,
              expiration: { maxEntries: 30, maxAgeSeconds: 60 * DAY },
              cacheableResponse: { statuses: [200] },
            },
          },
          {
            urlPattern: /^https:\/\/fonts\.googleapis\.com\/.*/,
            handler: "StaleWhileRevalidate",
            options: { cacheName: "google-fonts-css" },
          },
          {
            urlPattern: /^https:\/\/fonts\.gstatic\.com\/.*/,
            handler: "CacheFirst",
            options: {
              cacheName: "google-fonts",
              expiration: { maxEntries: 20, maxAgeSeconds: 365 * DAY },
              cacheableResponse: { statuses: [0, 200] },
            },
          },
          {
            // Map tiles you've already looked at, so a saved trip's map still shows offline.
            urlPattern: /^https:\/\/[a-c]\.tile\.openstreetmap\.org\/.*/,
            handler: "CacheFirst",
            options: {
              cacheName: "map-tiles",
              expiration: { maxEntries: 400, maxAgeSeconds: 14 * DAY },
              cacheableResponse: { statuses: [0, 200] },
            },
          },
        ],
      },
    }),
  ],
  server: {
    port: 5173,
    // In development the FastAPI backend runs on :8000; in production set VITE_API_URL.
    proxy: { "/api": "http://127.0.0.1:8000" },
  },
});
