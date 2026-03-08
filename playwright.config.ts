import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './app/tests',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: 'html',
  use: {
    baseURL: 'http://127.0.0.1:8080/viewer/',
    trace: 'on-first-retry',
  },
  webServer: {
    command: 'MAX_RETRIES=1 BYPASS_OVERSEER=1 python3 main.py',
    url: 'http://127.0.0.1:8080/viewer/',
    reuseExistingServer: true,
    timeout: 120000,
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
});
