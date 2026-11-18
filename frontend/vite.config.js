import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Port 5173 on 127.0.0.1 is one of the origins the local RoadAware API allows (CORS).
export default defineConfig({
  plugins: [react()],
  server: { host: "127.0.0.1", port: 5173, strictPort: true },
  preview: { host: "127.0.0.1", port: 5173, strictPort: true },
});
