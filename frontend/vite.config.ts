import react from "@vitejs/plugin-react";
import { defineConfig, loadEnv } from "vite";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, ".", "");
  return {
    // Set VITE_PUBLIC_BASE to a CDN URL (e.g. https://cdn.example.com/app/) to serve assets from a CDN.
    base: env.VITE_PUBLIC_BASE || "/",
    plugins: [react()],
    server: {
      port: 5173,
      proxy: {
        "/api": { target: env.VITE_API_PROXY || "http://localhost:8000", changeOrigin: false },
      },
    },
    build: {
      target: "es2020",
      sourcemap: false,
      cssCodeSplit: true,
      chunkSizeWarningLimit: 300,
      rollupOptions: {
        output: {
          manualChunks(id) {
            if (!id.includes("node_modules")) return undefined;
            if (/[\\/](react|react-dom|scheduler|react-router|react-router-dom)[\\/]/.test(id)) return "react";
            if (/[\\/](framer-motion|motion-dom|motion-utils)[\\/]/.test(id)) return "motion";
            return "vendor";
          },
        },
      },
    },
  };
});
