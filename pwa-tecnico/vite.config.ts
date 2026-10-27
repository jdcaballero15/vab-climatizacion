/// <reference types="vitest/config" />
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";
import { VitePWA } from "vite-plugin-pwa";

// La API se llama por /api del mismo sitio, como en Render (ADR 0010): así la cookie
// del refresh token es del mismo sitio. En local se reenvía al backend sin el prefijo.
const apiProxy = {
  "/api": {
    target: process.env.API_PROXY_TARGET ?? "http://localhost:8000",
    changeOrigin: true,
    rewrite: (path: string) => path.replace(/^\/api/, ""),
  },
};

// https://vite.dev/config/
export default defineConfig({
  server: { proxy: apiProxy },
  preview: { proxy: apiProxy },
  plugins: [
    react(),
    VitePWA({
      // 'prompt': la app avisa al técnico cuando hay una versión nueva (criterio 3).
      registerType: "prompt",
      includeAssets: ["favicon.svg"],
      manifest: {
        name: "OT Platform - Técnico",
        short_name: "OT Técnico",
        description: "App del técnico de VAB Climatización",
        lang: "es",
        display: "standalone",
        orientation: "portrait",
        background_color: "#eef1f7",
        theme_color: "#2563eb",
        start_url: "/",
        icons: [
          { src: "pwa-192x192.png", sizes: "192x192", type: "image/png" },
          { src: "pwa-512x512.png", sizes: "512x512", type: "image/png" },
          {
            src: "pwa-512x512.png",
            sizes: "512x512",
            type: "image/png",
            purpose: "maskable",
          },
        ],
      },
      workbox: {
        // Carcasa offline: se precachea el app shell (criterio 2).
        // Inter solo en sus subconjuntos latinos: sin conexión no cae a la fuente del sistema.
        globPatterns: ["**/*.{js,css,html,svg,png,ico}", "**/inter-latin-*.woff2"],
        navigateFallback: "index.html",
      },
      devOptions: { enabled: false },
    }),
  ],
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: "./src/test/setup.ts",
    // openapi-fetch (undici) necesita URL absoluta para construir el Request.
    env: { VITE_API_URL: "http://localhost/api" },
  },
});
