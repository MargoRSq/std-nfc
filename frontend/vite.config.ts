import path from "node:path";
import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const apiTarget = env.VITE_API_TARGET || "http://localhost:8001";

  return {
    plugins: [react()],
    resolve: {
      alias: { "@": path.resolve(__dirname, "./src") },
    },
    server: {
      port: 5173,
      host: "0.0.0.0",
      proxy: {
        "/api": { target: apiTarget, changeOrigin: true, followRedirects: true },
        "/c": { target: apiTarget, changeOrigin: true, followRedirects: true },
      },
    },
    build: {
      outDir: "dist",
      sourcemap: true,
      target: "es2022",
      rollupOptions: {
        output: {
          manualChunks(id) {
            if (
              id.includes("node_modules/recharts") ||
              id.includes("node_modules/victory-vendor") ||
              id.includes("node_modules/recharts-scale") ||
              id.includes("node_modules/d3-array") ||
              id.includes("node_modules/d3-color") ||
              id.includes("node_modules/d3-ease") ||
              id.includes("node_modules/d3-format") ||
              id.includes("node_modules/d3-interpolate") ||
              id.includes("node_modules/d3-path") ||
              id.includes("node_modules/d3-scale") ||
              id.includes("node_modules/d3-shape") ||
              id.includes("node_modules/d3-time") ||
              id.includes("node_modules/d3-time-format") ||
              id.includes("node_modules/d3-timer")
            ) {
              return "vendor-charts";
            }
            if (id.includes("node_modules/@radix-ui/")) {
              return "vendor-radix";
            }
            if (
              id.includes("node_modules/react/") ||
              id.includes("node_modules/react-dom/") ||
              id.includes("node_modules/react-router") ||
              id.includes("node_modules/scheduler/")
            ) {
              return "vendor-react";
            }
          },
        },
      },
    },
  };
});
