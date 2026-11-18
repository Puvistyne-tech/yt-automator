import { fileURLToPath } from "node:url";
import react from "@vitejs/plugin-react";
import { msw } from "msw/vite";
import { loadEnv } from "vite";
import { defineConfig } from "vitest/config";

const backendOrigin = process.env.AUTOTUBE_API_ORIGIN ?? "http://127.0.0.1:8000";
const servedFrom = "/";
const buildDir = "dist";

export default defineConfig(({ mode }) => {
  const useMocks = loadEnv(mode, process.cwd(), "VITE_").VITE_USE_MOCKS === "1";
  return {
    base: servedFrom,
    build: { outDir: buildDir, emptyOutDir: true },
    plugins: useMocks ? [react(), msw({ mode: "worker-only" })] : [react()],
    resolve: {
      alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) },
    },
    server: {
      proxy: useMocks ? {} : { "/api": backendOrigin },
    },
    test: {
      globals: true,
      environment: "jsdom",
      setupFiles: ["./tests/setup.ts"],
      include: ["tests/**/*.test.{ts,tsx}"],
    },
  };
});
