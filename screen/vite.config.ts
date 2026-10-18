import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// `npm run dev` serves the page with hot reload and forwards data requests to screen.py.
// 127.0.0.1, not localhost: Node may resolve localhost to IPv6, where screen.py isn't listening.
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": "http://127.0.0.1:8000",
      "/cache": "http://127.0.0.1:8000",
    },
  },
});
