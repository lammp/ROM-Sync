import { expect, test } from '@playwright/test'

test.beforeEach(async ({ request }) => {
  await request.post('/__reset')
})

test('with no device chosen the page lists the store’s system files', async ({ page }) => {
  await page.goto('/system-files/')
  await expect(page.getByRole('link', { name: 'System files' })).toHaveAttribute(
    'aria-current',
    'page',
  )
  await expect(page.getByRole('heading', { name: 'System files in the store' })).toBeVisible()
  await expect(page.getByRole('table', { name: 'System files in the store' })).toContainText(
    'gba_bios.bin',
  )
})

test('a device chosen in the header is read, and a system’s files are staged', async ({ page }) => {
  await page.goto('/system-files/')
  await page.getByRole('combobox', { name: 'Device' }).selectOption('dev-1')
  await expect(page.getByRole('heading', { name: 'Thor: system files' })).toBeVisible()
  await page.getByRole('button', { name: 'Refresh from device' }).click()
  await expect(page.getByText(/^device read/)).toBeVisible()
  await page.getByRole('button', { name: /^Game Boy Advance/ }).click()
  const detail = page.getByRole('article', { name: /^Game Boy Advance/ })
  await expect(detail).toContainText('Missing: gba_bios.bin')
  await detail.getByRole('button', { name: 'Add' }).click()
  await expect(page.getByText('Placed 1 file')).toBeVisible()
  await expect(detail).toContainText('current in ROM-Sync/bios/gba')
})

test('the device page says what its system files lack once read', async ({ page }) => {
  await page.goto('/system-files/')
  await page.getByRole('combobox', { name: 'Device' }).selectOption('dev-1')
  await page.getByRole('button', { name: 'Refresh from device' }).click()
  await expect(page.getByText(/^device read/)).toBeVisible()
  await page.goto('/devices/?id=dev-1')
  await expect(page.getByText('Game Boy Advance: missing gba_bios.bin')).toBeVisible()
})

test('a file added to the bios folder shows on return to the window, or on Check again', async ({
  page,
  request,
}) => {
  await request.post('/__seed/bios-removed')
  await page.goto('/system-files/')
  const row = page.getByRole('row', { name: /gba_bios\.bin/ })
  await expect(row).toContainText('missing')
  // the file is put back in Explorer; coming back to the window reads the folder again
  await request.post('/__seed/bios-restored')
  await page.evaluate(() =>
    document.dispatchEvent(new Event('visibilitychange', { bubbles: true })),
  )
  await expect(row).not.toContainText('missing')
  // and the button asks at once, without leaving the window
  await request.post('/__seed/bios-removed')
  await page.getByRole('button', { name: 'Check again' }).click()
  await expect(row).toContainText('missing')
  await expect(page.getByText(/^checked \d\d:\d\d:\d\d$/)).toBeVisible()
})
