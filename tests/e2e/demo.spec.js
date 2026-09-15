const { test, expect } = require('@playwright/test');

/*
 * Playwright demo recorder.
 *
 * This is intentionally excluded from the CI quality gate because video
 * recording is an artifact-generation task, not a required browser test.
 *
 * Run manually with:
 *   npx playwright test tests/e2e/demo.spec.js
 */

test('record SpeakTrain browser demo', async ({ page }) => {
  await page.goto('/login', { waitUntil: 'domcontentloaded' });

  await expect(page.locator('body')).toBeVisible();

  await page.screenshot({
    path: 'docs/screenshots/demo-login.png',
    fullPage: true
  });
});
