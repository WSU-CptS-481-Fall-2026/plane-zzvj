import { fileURLToPath } from "node:url";
import { defineConfig } from "vitest/config";

export default defineConfig({
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./", import.meta.url)),
      "next/navigation": fileURLToPath(new URL("./app/compat/next/navigation.ts", import.meta.url)),
    },
  },
  test: {
    environment: "jsdom",
    include: ["components/**/*.test.tsx"],
    pool: "forks",
    // Exercise instants whose UTC and local calendar dates differ.
    env: { TZ: "America/Los_Angeles" },
  },
});
