/// <reference types="vitest/config" />
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: "./src/test/setup.ts",
    // openapi-fetch (undici) necesita URL absoluta para construir el Request.
    env: { VITE_API_URL: "http://localhost/api" },
  },
});
