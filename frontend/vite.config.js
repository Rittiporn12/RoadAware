import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Normal mode: 127.0.0.1:5173 only (one of the origins the local RoadAware API allows, CORS).
// Phone mode (`npm run dev:phone`, see "Start Phone.command"): HTTPS on the Wi-Fi network, port 5174, so a phone on
// the same Wi-Fi can open it. HTTPS is required by phones for GPS, wake lock and audio. The phone never talks to
// 127.0.0.1 itself: /rapi and /rtts are forwarded by this dev server to the API (8000) and the voice proxy (8010)
// on the Mac, so no CORS change and no port other than 5174 is exposed.
export default defineConfig(async ({ mode }) => {
  if (mode !== "phone") {
    return {
      plugins: [react()],
      // GitHub Pages serves the site under /RoadAware/ (set by the Pages workflow); local dev stays at /
      base: process.env.ROADAWARE_BASE || "/",
      server: { host: "127.0.0.1", port: 5173, strictPort: true },
      preview: { host: "127.0.0.1", port: 5173, strictPort: true },
    };
  }
  const { default: basicSsl } = await import("@vitejs/plugin-basic-ssl");
  const forward = (target, prefix) => ({
    target,
    changeOrigin: true,
    rewrite: (p) => p.slice(prefix.length) || "/",
    configure: (proxy) => proxy.on("proxyReq", (req) => req.removeHeader("origin")),
  });
  return {
    plugins: [react(), basicSsl()],
    server: {
      host: "0.0.0.0",
      port: 5174,
      strictPort: true,
      proxy: { "/rapi": forward("http://127.0.0.1:8000", "/rapi"), "/rtts": forward("http://127.0.0.1:8010", "/rtts") },
    },
  };
});
