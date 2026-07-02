import { defineConfig } from "vitest/config";
import path from "node:path";

export default defineConfig({
  esbuild: {
    jsx: "automatic"
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname)
    }
  },
  test: {
    environment: "jsdom",
    exclude: ["node_modules/**", ".next/**", "e2e/**", "playwright-report/**", "test-results/**"],
    globals: true,
    setupFiles: ["./tests/setup.ts"]
  }
});
