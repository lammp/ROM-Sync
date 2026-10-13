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

test('the header stays in reach wherever Settings is scrolled to (F11-S45)', async ({ page }) => {
  await page.setViewportSize({ width: 900, height: 520 })
  await page.goto('/settings/')
  await page.getByRole('list', { name: 'Setup' }).waitFor()
  // jump to a section, then move focus down the page, as a person does
  await page.getByRole('button', { name: 'Go to Metadata' }).click()
  await page.getByRole('region', { name: /^Diagnostics/ }).scrollIntoViewIfNeeded()
  await page.getByRole('button', { name: /^ROMs folder/ }).focus()
  await page.keyboard.press('Tab')
  const scrolled = await page.evaluate(() => [
    document.documentElement.scrollTop,
    document.body.scrollTop,
  ])
  expect(scrolled, 'the document itself never scrolls, only the page under the header').toEqual([
    0, 0,
  ])
  const shell = await page.evaluate(() => document.querySelector('main')?.parentElement?.scrollTop)
  expect(shell, 'nor does the window under the header').toBe(0)
  const library = page.getByRole('link', { name: 'Library' })
  await expect(library).toBeInViewport()
  await library.click()
  await expect(page).toHaveURL(/\/$/)
})

test('a folder is chosen by browsing, never typed, and Cancel puts it back (F11-S45)', async ({
  page,
}) => {
  await page.goto('/settings/')
  const library = page.getByRole('region', { name: /^Library/ })
  await expect(library.getByRole('textbox', { name: 'ROMs folder' })).toHaveCount(0)
  await library.getByRole('button', { name: 'ROMs folder D:\\Games\\ROMs Choose folder…' }).click()
  const dialog = page.getByRole('dialog', { name: 'Choose the ROMs folder' })
  await expect(dialog.getByText('D:\\Games\\ROMs', { exact: true })).toBeVisible()
  await dialog.getByRole('button', { name: 'Up' }).click()
  await dialog.getByRole('button', { name: 'Up' }).click()
  await dialog.getByRole('button', { name: 'Up' }).click()
  await expect(dialog.getByRole('list', { name: 'Drives' })).toBeVisible()
  await dialog.getByRole('button', { name: 'D:\\' }).click()
  await dialog.getByRole('button', { name: 'Games' }).click()
  await dialog.getByRole('button', { name: 'ROMs', exact: true }).click()
  await dialog.getByRole('button', { name: 'snes' }).click()
  await dialog.getByRole('button', { name: 'Choose this folder' }).click()
  await expect(dialog).toHaveCount(0)
  await expect(
    library.getByRole('button', { name: 'ROMs folder D:\\Games\\ROMs\\snes Choose folder…' }),
  ).toBeVisible()
  await expect(library.getByRole('heading')).toContainText('edited')
  await library.getByRole('button', { name: 'Cancel' }).click()
  await expect(
    library.getByRole('button', { name: 'ROMs folder D:\\Games\\ROMs Choose folder…' }),
  ).toBeVisible()
  await expect(library.getByRole('heading')).not.toContainText('edited')
})

test('the ADB executable is chosen as a file (F11-S45)', async ({ page }) => {
  await page.goto('/settings/')
  const transports = page.getByRole('region', { name: /^Transports and tools/ })
  await transports.getByRole('button', { name: /^ADB executable/ }).click()
  const dialog = page.getByRole('dialog', { name: 'Choose the ADB executable' })
  await dialog.getByRole('button', { name: 'D:\\' }).click()
  await dialog.getByRole('button', { name: 'Games' }).click()
  await expect(dialog.getByRole('button', { name: 'README.txt' })).toHaveCount(0)
  await dialog.getByRole('button', { name: '_tools' }).click()
  await dialog.getByRole('button', { name: 'platform-tools' }).click()
  await expect(dialog.getByRole('button', { name: 'AdbWinApi.dll' })).toHaveCount(0)
  await dialog.getByRole('button', { name: 'adb.exe' }).click()
  await dialog.getByRole('button', { name: 'Choose this file' }).click()
  await expect(
    transports.getByRole('button', {
      name: 'ADB executable D:\\Games\\_tools\\platform-tools\\adb.exe Choose file…',
    }),
  ).toBeVisible()
})

test('every dialog closes by its close button, Escape, or a click outside (F11-S45)', async ({
  page,
}) => {
  await page.goto('/settings/')
  const library = page.getByRole('region', { name: /^Library/ })
  const open = async () => {
    await library.getByRole('button', { name: /^ROMs folder/ }).click()
    await expect(page.getByRole('dialog')).toBeVisible()
  }
  await open()
  await page.getByRole('button', { name: 'Close' }).click()
  await expect(page.getByRole('dialog')).toHaveCount(0)
  await open()
  await page.keyboard.press('Escape')
  await expect(page.getByRole('dialog')).toHaveCount(0)
  await open()
  await page.mouse.click(5, 300)
  await expect(page.getByRole('dialog')).toHaveCount(0)
  // a confirmation as well as a chooser
  await library.getByRole('button', { name: 'Rescan ROMs folder' }).click()
  await expect(page.getByRole('dialog', { name: 'Rescan the ROMs folder' })).toBeVisible()
  await page.mouse.click(5, 300)
  await expect(page.getByRole('dialog')).toHaveCount(0)
})
