const { test, expect } = require('@playwright/test');
const fs = require('fs');
const path = require('path');

test('record a passing SpeakTrain browser demo', async ({ browser }) => {
  const outputDir = path.resolve('docs/demo');
  fs.mkdirSync(outputDir, { recursive: true });

  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    recordVideo: {
      dir: 'test-results/demo-videos',
      size: { width: 1440, height: 900 }
    }
  });

  const page = await context.newPage();

  await page.goto('/login', { waitUntil: 'domcontentloaded' });
  await expect(page.locator('body')).toBeVisible();

  await page.screenshot({
    path: 'docs/screenshots/demo-login.png',
    fullPage: true
  });

  await page.waitForTimeout(1500);

  const video = page.video();

  await context.close();

  if (video) {
    await video.saveAs(
      path.join(outputDir, 'speaktrain-playwright-demo.webm')
    );
  }

  expect(
    fs.existsSync(
      path.join(outputDir, 'speaktrain-playwright-demo.webm')
    )
  ).toBeTruthy();
});
