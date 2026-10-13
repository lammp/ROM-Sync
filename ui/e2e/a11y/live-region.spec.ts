import { expect, test, type Locator, type Page } from '@playwright/test'

// F11-S36: every toast is announced. A live region is only read out when its
// content changes after it is in the page, so each page must hold the one
// region from the start, and every toast must land in that same element.

const region = (page: Page) => page.getByRole('status', { name: 'Notifications' })

/** Marks the region the page loaded with, so a later look can tell it is the same element. */
async function original(page: Page): Promise<Locator> {
  const r = region(page)
  await expect(r).toHaveCount(1)
  await expect(r).toHaveAttribute('aria-live', 'polite')
  await r.evaluate((el) => el.setAttribute('data-original', 'yes'))
  return r
}

async function announced(r: Locator, text: string | RegExp) {
  await expect(r).toContainText(text)
  await expect(r).toHaveAttribute('data-original', 'yes')
}

test.beforeEach(async ({ request }) => {
  await request.post('/__reset')
})

test('announces_every_toast: every page holds the one live region from the start', async ({
  page,
}) => {
  for (const path of [
    '/',
    '/devices/',
    '/devices/?id=dev-1',
    '/system-files/',
    '/settings/',
    '/recover/',
  ]) {
    await page.goto(path)
    await original(page)
    await expect(region(page)).toHaveText('')
  }
})

test('announces_every_toast: a saved section is announced', async ({ page }) => {
  await page.goto('/settings/#sync')
  const r = await original(page)
  const sync = page.getByRole('region', { name: /^Sync behaviour/ })
  await sync.getByRole('textbox', { name: 'Keep free on the device' }).fill('1 GB')
  await sync.getByRole('button', { name: 'Save sync behaviour and guards' }).click()
  await announced(r, 'Sync behaviour and guards saved')
})

test('announces_every_toast: a refusal is announced', async ({ page, request }) => {
  await request.post('/__seed/recover')
  await page.goto('/recover/')
  const r = await original(page)
  await page.getByRole('button', { name: 'Recover Clash (USA).sfc' }).click()
  await announced(r, 'the store already has snes/Clash (USA).sfc; nothing was replaced')
})

test('announces_every_toast: a sync ending is announced on whichever page is open', async ({
  page,
}) => {
  await page.goto('/devices/?id=dev-1')
  await page.getByRole('button', { name: 'Sync', exact: true }).click()
  await page
    .getByRole('dialog', { name: 'Sync Thor' })
    .getByRole('button', { name: 'Start' })
    .click()
  await page.getByRole('link', { name: 'Library' }).click()
  const r = await original(page)
  await announced(r, /^Thor synced: sent 10, removed 0/)
})

test('announces_every_toast: a job ending is announced, as is each one after it', async ({
  page,
}) => {
  await page.goto('/devices/?id=dev-1')
  const r = await original(page)
  await page.getByRole('button', { name: 'Scan device' }).click()
  await announced(r, 'Read 1 game from the device')
  await page.getByRole('button', { name: 'Write ROM-Sync.json' }).click()
  await page
    .getByRole('dialog', { name: 'Write ROM-Sync.json' })
    .getByRole('button', { name: 'Write' })
    .click()
  await announced(r, 'ROM-Sync.json written')
})
