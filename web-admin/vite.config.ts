/// <reference types="vitest/config" />
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

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
  plugins: [react()],
  server: { proxy: apiProxy },
  preview: { proxy: apiProxy },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: "./src/test/setup.ts",
    // openapi-fetch (undici) necesita URL absoluta para construir el Request.
    env: { VITE_API_URL: "http://localhost/api" },
  },
});
