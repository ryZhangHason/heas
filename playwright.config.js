import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "docs/tests/e2e",
  timeout: 120000,
  use: {
    baseURL: "http://127.0.0.1:4173",
    headless: true,
  },
  webServer: {
    command: "python3 -m http.server 4173 --bind 127.0.0.1 --directory docs",
    port: 4173,
    reuseExistingServer: true,
    timeout: 120000,
  },
});
