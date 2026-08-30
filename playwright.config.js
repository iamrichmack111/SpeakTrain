const {defineConfig, devices} = require('@playwright/test');

const python = process.env.PYTHON_EXECUTABLE || 'python3';
const database = require('path').resolve(__dirname, 'instance', 'playwright.sqlite3');

module.exports = defineConfig({
  testDir: './tests/e2e',
  timeout: 45_000,
  expect: {timeout: 8_000},
  fullyParallel: false,
  retries: process.env.CI ? 2 : 0,
  reporter: process.env.CI ? [['line'], ['html', {open: 'never'}]] : 'list',
  use: {
    baseURL: 'http://127.0.0.1:8096',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    ...devices['Desktop Chrome'],
    viewport: {width: 1440, height: 1000}
  },
  webServer: {
    command: `${python} scripts/seed_playwright.py --fresh --database ${database} && SPEAKTRAIN_DATABASE=${database} SPEAKTRAIN_PORT=8096 SPEAKTRAIN_DEBUG=0 ${python} app.py`,
    url: 'http://127.0.0.1:8096/healthz',
    reuseExistingServer: false,
    timeout: 120_000
  }
});
