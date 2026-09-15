const {test, expect} = require('@playwright/test');
const path = require('path');

const demoVideo = path.join(process.cwd(), 'docs', 'demo', 'speaktrain-playwright-demo.webm');

test.use({video: 'on'});

test('record a passing SpeakTrain browser demo', async ({page}) => {
  test.setTimeout(90_000);

  await page.goto('/login');
  await expect(page.getByRole('heading', {name: 'Welcome back'})).toBeVisible();
  await page.waitForTimeout(700);

  await page.getByLabel('Username').fill('admin');
  await page.getByLabel('Password').fill('admin');
  await page.waitForTimeout(500);
  await page.getByRole('button', {name: 'Sign in'}).click();

  await expect(page.getByText('YOUR ADAPTIVE SESSION')).toBeVisible();
  await expect(page.locator('#target')).not.toHaveText('');
  await page.waitForTimeout(1200);

  await page.getByRole('button', {name: 'Phrase practice'}).click();
  await expect(page.locator('#practice')).toHaveClass(/active/);
  await page.waitForTimeout(1300);

  await page.getByRole('button', {name: 'Courses'}).click();
  await expect(page.getByText('Build conversation in stages')).toBeVisible();
  await page.waitForTimeout(1200);

  await page.getByRole('button', {name: 'OPI simulator'}).click();
  await expect(page.getByText('UNREHEARSED RESPONSE')).toBeVisible();
  await page.waitForTimeout(1200);

  await page.getByRole('button', {name: 'Vocabulary test'}).click();
  await expect(page.getByText('VOCABULARY RECALL')).toBeVisible();
  await page.waitForTimeout(1100);

  await page.getByRole('button', {name: 'Conjugation drill'}).click();
  await expect(page.getByText('CONJUGATION RECALL')).toBeVisible();
  await page.waitForTimeout(1100);

  await page.getByRole('button', {name: 'Conversation'}).click();
  await expect(page.locator('#conversationPrompt')).toBeVisible();
  await page.waitForTimeout(1200);

  await page.getByRole('button', {name: 'Vocabulary & sentence lab'}).click();
  await expect(page.getByText('SEARCHABLE VOCABULARY')).toBeVisible();
  await page.waitForTimeout(1200);

  await page.getByRole('button', {name: 'Progress'}).click();
  await expect(page.getByRole('heading', {name: 'Your performance'})).toBeVisible();
  await page.waitForTimeout(1200);

  await page.getByRole('link', {name: 'Admin'}).click();
  await expect(page.getByText('CURRICULUM STUDIO')).toBeVisible();
  await page.waitForTimeout(1400);

  const video = page.video();
  if (!video) throw new Error('Playwright video recording was not enabled');
  await page.close();
  await video.saveAs(demoVideo);
});
