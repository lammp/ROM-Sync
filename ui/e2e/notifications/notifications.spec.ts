import { expect, test } from '@playwright/test'

test.beforeEach(async ({ request }) => {
  await request.post('/__reset')
})

const bell = (page: import('@playwright/test').Page) =>
  page.getByRole('button', { name: /^Notifications/ })

test('a setup step still to do waits in the bell, and leads to its settings tab (F11-S47)', async ({
  page,
}) => {
  await page.goto('/')
  await expect(bell(page)).toHaveAccessibleName('Notifications, 1 unread')
  await bell(page).click()
  const list = page.getByRole('dialog', { name: 'Notifications' })
  await expect(list).toContainText('Add IGDB credentials for covers and details')
  await expect(bell(page)).toHaveAccessibleName('Notifications')
  await list.getByRole('button', { name: 'Open' }).click()
  await expect(page).toHaveURL(/\/settings\/?#metadata$/)
  await expect(page.getByRole('tab', { name: 'Metadata and artwork' })).toHaveAttribute(
    'aria-selected',
    'true',
  )
})

test('a scan the engine ran on its own is said, kept, and cleared (F11-S47)', async ({
  page,
  request,
}) => {
  await page.goto('/')
  await expect(bell(page)).toHaveAccessibleName('Notifications, 1 unread')
  await request.post('/__seed/scan-ended')
  await expect(bell(page)).toHaveAccessibleName('Notifications, 2 unread', { timeout: 10_000 })
  await expect(page.getByRole('status', { name: 'Notifications' })).toContainText(
    'Scan finished: 40 games found',
  )
  await bell(page).click()
  const list = page.getByRole('dialog', { name: 'Notifications' })
  await expect(list.getByRole('listitem').first()).toContainText('Scan finished: 40 games found')
  await list.getByRole('button', { name: 'Clear Scan finished: 40 games found' }).click()
  await expect(list).not.toContainText('Scan finished')
  // cleared stays cleared over a reload
  await page.reload()
  await bell(page).click()
  await expect(page.getByRole('dialog', { name: 'Notifications' })).not.toContainText(
    'Scan finished',
  )
  await page.getByRole('button', { name: 'Clear all' }).click()
  await expect(page.getByRole('dialog', { name: 'Notifications' })).toContainText(
    'Nothing to report.',
  )
})

test('a device pulled out and plugged back in is said, wherever the person is (F11-S47)', async ({
  page,
  request,
}) => {
  await page.clock.install()
  // the first look at what is plugged in is the baseline: nothing is said for it
  const first = page.waitForResponse((r) => r.url().endsWith('/api/v1/devices'))
  await page.goto('/system-files/')
  await first
  await request.post('/__seed/thor-unplugged')
  await page.clock.fastForward(16_000)
  await expect(page.getByRole('status', { name: 'Notifications' })).toContainText(
    'Thor disconnected',
  )
  await request.post('/__seed/thor-plugged')
  await page.clock.fastForward(16_000)
  await expect(page.getByRole('status', { name: 'Notifications' })).toContainText('Thor connected')
  await bell(page).click()
  // the device's own notifications, newest first; a setup step may sit among them
  const items = page
    .getByRole('dialog', { name: 'Notifications' })
    .getByRole('listitem')
    .filter({ hasText: /^Thor / })
  await expect(items).toHaveCount(2)
  await expect(items.nth(0)).toContainText('Thor connected')
  await expect(items.nth(1)).toContainText('Thor disconnected')
})

test('the list closes on its close button, Escape and a click outside', async ({ page }) => {
  await page.goto('/')
  const list = page.getByRole('dialog', { name: 'Notifications' })
  await bell(page).click()
  await list.getByRole('button', { name: 'Close' }).click()
  await expect(list).toHaveCount(0)
  await bell(page).click()
  await page.keyboard.press('Escape')
  await expect(list).toHaveCount(0)
  await bell(page).click()
  await page.mouse.click(20, 400)
  await expect(list).toHaveCount(0)
})
