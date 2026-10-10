import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The world server (server/api.py) serves state and actions under /api.
// The agent harness (`harness serve`) is reached under /harness (decision 0007).
// Ports come from the environment (the launcher sets them); defaults 8000 / 5173 / 8090.
const apiPort = process.env.PORT ?? "8000";
const harnessPort = process.env.HARNESS_PORT ?? "8090";

export default defineConfig({
  plugins: [react()],
  // The world server as the harness reaches it; sent with "Start agent".
  define: { __WORLD_URL__: JSON.stringify(`http://127.0.0.1:${apiPort}`) },
  server: {
    port: Number(process.env.UI_PORT ?? 5173),
    proxy: {
      "/api": { target: `http://localhost:${apiPort}`, ws: true },
      "/harness": { target: `http://127.0.0.1:${harnessPort}`, rewrite: (p) => p.replace(/^\/harness/, "") },
    },
  },
});
