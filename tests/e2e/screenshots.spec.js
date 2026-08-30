const {test, expect} = require('@playwright/test');
const path = require('path');

const shot = name => path.join(process.cwd(), 'docs', 'screenshots', name);

test('capture every public documentation page from a fresh admin login', async ({page, context}) => {
  await page.goto('/login');
  await expect(page.getByRole('heading', {name: 'Welcome back'})).toBeVisible();
  await page.screenshot({path: shot('01-login.png'), fullPage: true, animations: 'disabled'});

  // Authenticate against the isolated Playwright database.
  // BrowserContext.request shares cookies with the browser context.
  const login = await context.request.post('/login', {
    form: {
      username: 'admin',
      password: 'admin',
    },
    maxRedirects: 0,
  });

  expect([302, 303]).toContain(login.status());

  await page.goto('/');
  await expect(page.getByText('YOUR ADAPTIVE SESSION')).toBeVisible();
  await page.screenshot({path: shot('02-today-dashboard.png'), fullPage: true, animations: 'disabled'});

  // Wait until the asynchronous catalog/render cycle has populated practice data.
  await expect(page.locator('#target')).not.toHaveText('');

  // Target the actual application tab rather than relying on accessible-name timing.
  await page.locator('button[data-view="practice"]').click();

  await expect(page.locator('#practice')).toHaveClass(/active/);
  await expect(page.locator('#target')).toBeVisible();

  await page.screenshot({path: shot('03-phrase-practice.png'), fullPage: true, animations: 'disabled'});

  await page.getByRole('button', {name: 'Courses'}).click();
  await expect(page.getByText('Build conversation in stages')).toBeVisible();
  await page.screenshot({path: shot('04-courses.png'), fullPage: true, animations: 'disabled'});

  await page.getByRole('button', {name: 'OPI simulator'}).click();
  await expect(page.getByText('UNREHEARSED RESPONSE')).toBeVisible();
  await page.screenshot({path: shot('05-opi-simulator.png'), fullPage: true, animations: 'disabled'});

  await page.getByRole('button', {name: 'Vocabulary test'}).click();
  await expect(page.getByText('VOCABULARY RECALL')).toBeVisible();
  await page.screenshot({path: shot('06-vocabulary-test.png'), fullPage: true, animations: 'disabled'});

  await page.getByRole('button', {name: 'Conjugation drill'}).click();
  await expect(page.getByText('CONJUGATION RECALL')).toBeVisible();
  await page.screenshot({path: shot('07-conjugation-drill.png'), fullPage: true, animations: 'disabled'});

  await page.getByRole('button', {name: 'Conversation'}).click();
  await expect(page.locator('#conversationPrompt')).toBeVisible();
  await page.screenshot({path: shot('08-conversation.png'), fullPage: true, animations: 'disabled'});

  await page.getByRole('button', {name: 'Vocabulary & sentence lab'}).click();
  await expect(page.getByText('SEARCHABLE VOCABULARY')).toBeVisible();
  await page.screenshot({path: shot('09-vocabulary-sentence-lab.png'), fullPage: true, animations: 'disabled'});

  await page.getByRole('button', {name: 'Progress'}).click();
  await expect(page.getByRole('heading', {name: 'Your performance'})).toBeVisible();
  await page.screenshot({path: shot('10-progress.png'), fullPage: true, animations: 'disabled'});

  await page.getByRole('link', {name: 'Admin'}).click();
  await expect(page.getByText('CURRICULUM STUDIO')).toBeVisible();
  await page.screenshot({path: shot('11-admin-curriculum.png'), fullPage: true, animations: 'disabled'});

  await page.goto('/report/weekly');
  await expect(page.getByText('WEEKLY STUDY & GRADE REPORT')).toBeVisible();
  await page.screenshot({path: shot('12-weekly-report.png'), fullPage: true, animations: 'disabled'});
});

test('health endpoint and protected application shell', async ({page}) => {
  const health = await page.request.get('/healthz');
  expect(health.ok()).toBeTruthy();
  expect(await health.json()).toEqual({status: 'ok', service: 'speaktrain'});
  await page.goto('/');
  await expect(page).toHaveURL(/\/login$/);
});
