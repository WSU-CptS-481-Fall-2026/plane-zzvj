import { fileURLToPath } from "node:url";
import { defineConfig } from "vitest/config";

const source = (path: string) => fileURLToPath(new URL(path, import.meta.url));

export default defineConfig({
  resolve: {
    alias: {
      "@": source("./"),
      "@plane/constants": source("../../packages/constants/src/index.ts"),
      "@plane/types": source("../../packages/types/src/index.ts"),
      "@plane/hooks": source("../../packages/hooks/src/index.ts"),
      "@plane/i18n": source("../../packages/i18n/src/index.ts"),
      "@plane/blocks/icons": source("../../packages/blocks/src/icons/index.ts"),
    },
  },
  oxc: { jsx: { runtime: "automatic" } },
  css: { postcss: { plugins: [] } },
  test: {
    environment: "jsdom",
    include: ["tests/**/*.test.tsx"],
    maxWorkers: 1,
    isolate: true,
  },
});
