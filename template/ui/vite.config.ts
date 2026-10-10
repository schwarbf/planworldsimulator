import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The world server (server/api.py) serves state and actions under /api.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: { "/api": { target: "http://localhost:8000", ws: true } },
  },
});
