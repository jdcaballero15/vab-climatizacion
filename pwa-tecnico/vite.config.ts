/// <reference types="vitest/config" />
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";
import { VitePWA } from "vite-plugin-pwa";

// https://vite.dev/config/
export default defineConfig({
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
        background_color: "#ffffff",
        theme_color: "#1f6feb",
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
        globPatterns: ["**/*.{js,css,html,svg,png,ico}"],
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
