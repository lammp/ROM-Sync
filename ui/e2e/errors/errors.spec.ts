import { expect, test, type Page } from '@playwright/test'

// Every view, with its main reads failing: it says so with Retry rather than
// waiting for ever (no_permanent_loading), and Retry brings it back once the
// engine answers again (retry_everywhere).
const VIEWS: {
  name: string
  path: string
  fail: string[]
  shown: (page: Page) => Promise<void>
}[] = [
  {
    name: 'library',
    path: '/',
    fail: ['/api/v1/library'],
    shown: (page) =>
      expect(page.getByRole('toolbar', { name: 'Library' })).toContainText('40 of 40'),
  },
  {
    name: 'devices',
    path: '/devices/',
    fail: ['/api/v1/profiles'],
    shown: (page) => expect(page.getByRole('article', { name: 'Thor' })).toBeVisible(),
  },
  {
    name: 'one device',
    path: '/devices/?id=dev-1',
    fail: ['/api/v1/profiles'],
    shown: (page) => expect(page.getByRole('heading', { name: /^Thor/ })).toBeVisible(),
  },
  {
    name: 'system files',
    path: '/system-files/',
    fail: ['/api/v1/sysfiles'],
    shown: (page) =>
      expect(page.getByRole('table', { name: 'System files in the store' })).toBeVisible(),
  },
  {
    name: 'settings',
    path: '/settings/',
    fail: ['/api/v1/settings'],
    shown: (page) => expect(page.getByRole('region', { name: /^Library/ })).toBeVisible(),
  },
  {
    name: 'recover',
    path: '/recover/',
    fail: ['/api/v1/devices/YWRiAHNlcmlhbC0x/recover'],
    shown: (page) =>
      expect(page.getByText('Everything on this device is in the store.')).toBeVisible(),
  },
]

test.beforeEach(async ({ request }) => {
  await request.post('/__reset')
})

for (const view of VIEWS) {
  test(`${view.name}: no_permanent_loading and retry_everywhere, a failed read says so and Retry recovers`, async ({
    page,
    request,
  }) => {
    await request.post('/__fail', { data: { paths: view.fail } })
    await page.goto(view.path)
    const retry = page.getByRole('alert').getByRole('button', { name: 'Retry' }).first()
    await expect(retry).toBeVisible({ timeout: 15_000 })
    await expect(page.getByText(/^(loading|checking|looking)…$/)).toHaveCount(0)
    await request.post('/__fail', { data: { paths: [] } })
    await retry.click()
    await view.shown(page)
  })
}
