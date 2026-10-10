/// <reference types="vitest/config" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The world server (server/api.py) serves state and actions under /api.
// The agent harness (`harness serve`) is reached under /harness (decision 0007).
// Ports come from the environment (the launcher sets them); defaults 8000 / 5173 / 8090.
const apiPort = process.env.PORT ?? "8000";

// Relative asset URLs: the built UI is served behind /api/play/<id>/.
// The cache lives in the world's own folder: node_modules is shared between worlds and
// may be read-only (in Docker it belongs to another user).
export default defineConfig({
  base: "./",
  cacheDir: ".vite-cache",
  plugins: [react()],
  test: {
    environment: "jsdom",
    include: ["src/**/*.test.tsx"],
    setupFiles: ["src/test-setup.ts"],
    cache: { dir: ".vite-cache/vitest" },
  },
  server: {
    port: Number(process.env.UI_PORT ?? 5173),
    proxy: {
      "/api": { target: `http://localhost:${apiPort}`, ws: true },
      "/harness": { target: `http://localhost:${apiPort}` },
    },
  },
});
