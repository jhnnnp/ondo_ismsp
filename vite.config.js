import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  build: {
    emptyOutDir: true,
    outDir: "src/isms_pii_toolkit/web/control_map/react-dist",
    rollupOptions: {
      input: "frontend/report-editor/main.jsx",
      output: {
        entryFileNames: "report-editor.js",
        assetFileNames: "report-editor.[ext]",
      },
    },
  },
});
