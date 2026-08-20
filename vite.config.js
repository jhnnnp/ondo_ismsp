import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  build: {
    emptyOutDir: true,
    outDir: "src/isms_pii_toolkit/web/control_map/react-dist",
    rollupOptions: {
      input: {
        workspace: "src/isms_pii_toolkit/web/control_map/app.js",
        "report-editor": "frontend/report-editor/main.jsx",
      },
      output: {
        entryFileNames: "[name].js",
        assetFileNames: (assetInfo) => (
          assetInfo.name === "report-editor.css"
            ? "report-editor.css"
            : "[name].[ext]"
        ),
      },
    },
  },
});
