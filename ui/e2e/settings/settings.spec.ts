import { expect, test } from '@playwright/test'

test.beforeEach(async ({ request }) => {
  await request.post('/__reset')
})

test('settings opens on setup, then the sections in first-run order', async ({ page }) => {
  await page.goto('/settings/')
  await expect(page.getByRole('link', { name: 'Settings' })).toHaveAttribute('aria-current', 'page')
  await expect(page.getByRole('list', { name: 'Setup' })).toContainText('to do')
  await expect(page.getByRole('heading', { level: 2 })).toHaveText([
    'Setup',
    /^Library/,
    /^Metadata and artwork/,
    /^Tag suggestions/,
    /^Transports and tools/,
    /^Sync behaviour and guards/,
    /^Data and storage/,
    /^Diagnostics/,
  ])
})

test('a section saves on its own and the value is kept over a reload', async ({ page }) => {
  await page.goto('/settings/')
  const sync = page.getByRole('region', { name: /^Sync behaviour/ })
  await sync.getByRole('textbox', { name: 'Keep free on the device' }).fill('1 GB')
  await sync.getByRole('button', { name: 'Save sync behaviour and guards' }).click()
  await expect(page.getByText('Sync behaviour and guards saved')).toBeVisible()
  await page.reload()
  await expect(
    page
      .getByRole('region', { name: /^Sync behaviour/ })
      .getByRole('textbox', { name: 'Keep free on the device' }),
  ).toHaveValue('1.00 GB')
})

test('credentials are added, tested and saved without the secret coming back', async ({ page }) => {
  await page.goto('/settings/')
  const meta = page.getByRole('region', { name: /^Metadata and artwork/ })
  await meta.getByRole('textbox', { name: 'Twitch client ID' }).fill('my-client')
  await meta.getByRole('button', { name: 'Add credentials' }).click()
  await meta.getByLabel('New client secret').fill('a-secret-that-is-long-enough')
  await meta.getByRole('button', { name: 'Test connection' }).click()
  await expect(meta.getByRole('status')).toHaveText('connected: token, api ok')
  await meta.getByRole('button', { name: 'Save metadata and artwork' }).click()
  await expect(meta).toContainText('28 characters · not shown again')
  await expect(page.locator('input[type="password"]')).toHaveCount(0)
  await expect(page.getByText(/^Setup complete\./)).toBeVisible()
})
