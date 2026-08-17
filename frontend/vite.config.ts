import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import { resolve } from "node:path";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  // Assets are loaded from file:// or the bundled http server, never a
  // domain root — relative base is required or every asset 404s.
  base: "./",
  resolve: { alias: { "@": resolve(__dirname, "src") } },
  build: {
    outDir: resolve(__dirname, "../src/norefund/web"),
    emptyOutDir: true,
    target: "es2022",
    sourcemap: false,
  },
  server: { port: 5173, strictPort: true },
});
