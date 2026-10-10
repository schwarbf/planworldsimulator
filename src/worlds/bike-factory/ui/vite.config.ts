import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The world server (server/api.py) serves state and actions under /api.
// Ports come from the environment (the launcher sets them); defaults 8000 / 5173.
const apiPort = process.env.PORT ?? "8000";

export default defineConfig({
  plugins: [react()],
  server: {
    port: Number(process.env.UI_PORT ?? 5173),
    proxy: { "/api": { target: `http://localhost:${apiPort}`, ws: true } },
  },
});
