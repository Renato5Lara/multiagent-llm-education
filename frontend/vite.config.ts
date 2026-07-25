import path from "path"
import react from "@vitejs/plugin-react"
import { defineConfig } from "vite"

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    port: 5173,
    // Habilita self.crossOriginIsolated — requisito de SharedArrayBuffer
    // para el input() interactivo real de Épica B (Worker + Atomics.wait,
    // SPIKE-B1-PYODIDE-WORKER-STDIN.md; ver ENGINEERING-GATE-EPICA-B.md
    // §8: auditoría de recursos cross-origin, cero incompatibilidades
    // encontradas — Google Fonts + CDN de Pyodide ya envían
    // Cross-Origin-Resource-Policy: cross-origin). Espejo de producción
    // en frontend/vercel.json.
    headers: {
      "Cross-Origin-Opener-Policy": "same-origin",
      "Cross-Origin-Embedder-Policy": "require-corp",
    },
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
      "/health": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: "dist",
    sourcemap: false,
  },
})
