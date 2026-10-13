import { expect, test } from '@playwright/test'

test.beforeEach(async ({ request }) => {
  await request.post('/__reset')
})

test('settings opens on its first tab, the groups as tabs in first-run order (F11-S48)', async ({
  page,
}) => {
  await page.goto('/settings/')
  const cog = page.getByRole('link', { name: 'Settings' })
  await expect(cog).toHaveAttribute('aria-current', 'page')
  await expect(cog).toHaveText('')
  await expect(page.getByRole('tab')).toHaveText([
    'Library',
    'Metadata and artwork',
    'Tag suggestions',
    'Transports and tools',
    'Sync behaviour and guards',
    'Data and storage',
    'Diagnostics',
  ])
  await expect(page.getByRole('tab', { name: 'Library' })).toHaveAttribute('aria-selected', 'true')
  await expect(page.getByRole('list', { name: 'Setup' })).toHaveCount(0)
})

test('a tab saves on its own, and the open tab and value are kept over a reload', async ({
  page,
}) => {
  await page.goto('/settings/')
  await page.getByRole('tab', { name: 'Sync behaviour and guards' }).click()
  const sync = page.getByRole('region', { name: /^Sync behaviour/ })
  await sync.getByRole('combobox', { name: 'Keep free on the device' }).selectOption('1.00 GB')
  await expect(
    page.getByRole('tab', { name: 'Sync behaviour and guards, unsaved changes' }),
  ).toBeVisible()
  await sync.getByRole('button', { name: 'Save sync behaviour and guards' }).click()
  await expect(page.getByText('Sync behaviour and guards saved')).toBeVisible()
  await expect(page.getByRole('tab', { name: 'Sync behaviour and guards' })).toBeVisible()
  await page.reload()
  await expect(page.getByRole('tab', { name: 'Sync behaviour and guards' })).toHaveAttribute(
    'aria-selected',
    'true',
  )
  await expect(
    page
      .getByRole('region', { name: /^Sync behaviour/ })
      .getByRole('combobox', { name: 'Keep free on the device' }),
  ).toHaveValue('1.00 GB')
})

test('credentials are added, tested and saved without the secret coming back', async ({ page }) => {
  await page.goto('/settings/#metadata')
  const meta = page.getByRole('region', { name: /^Metadata and artwork/ })
  await meta.getByRole('textbox', { name: 'Twitch client ID' }).fill('my-client')
  const secret = meta.getByLabel('Client secret', { exact: true })
  await secret.fill('a-secret-that-is-long-enough')
  const test = meta.getByRole('button', { name: 'Test connection' })
  await test.click()
  await expect(meta.getByRole('status')).toHaveText('connected: token, api ok')
  await expect(test.locator('svg')).toHaveAttribute('data-icon', 'tick')
  await meta.getByRole('button', { name: 'Save metadata and artwork' }).click()
  await expect(meta).toContainText('28 characters. A saved secret is never shown again.')
  // saved: both locked, and the secret is dots, never its value
  await expect(meta.getByRole('textbox', { name: 'Twitch client ID' })).toHaveAttribute('readonly')
  await expect(secret).toHaveAttribute('readonly')
  await expect(secret).not.toHaveValue(/a-secret/)
  await expect(meta.getByRole('button', { name: 'Show the client secret' })).toHaveCount(0)
  // the setup step it answered leaves the notifications
  await page.getByRole('button', { name: /^Notifications/ }).click()
  await expect(page.getByRole('dialog', { name: 'Notifications' })).not.toContainText('IGDB')
})

test('the header stays in reach wherever Settings is scrolled to (F11-S45)', async ({ page }) => {
  await page.setViewportSize({ width: 900, height: 520 })
  await page.goto('/settings/#data')
  await page.getByRole('table', { name: 'Upkeep' }).waitFor()
  // move focus to the foot of a long tab, as a person does
  await page.getByRole('table', { name: 'Upkeep' }).scrollIntoViewIfNeeded()
  await page.getByRole('button', { name: 'Reveal the data folder' }).focus()
  for (let i = 0; i < 12; i++) await page.keyboard.press('Tab')
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
  await page.goto('/settings/#transports')
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

test('the metadata runs from the top of its tab, and a refresh asks first (F11-S52)', async ({
  page,
}) => {
  await page.goto('/settings/#metadata')
  const meta = page.getByRole('region', { name: /^Metadata and artwork/ })
  await meta.getByRole('textbox', { name: 'Twitch client ID' }).fill('my-client')
  await meta.getByLabel('Client secret', { exact: true }).fill('a-secret-that-is-long-enough')
  await meta.getByRole('button', { name: 'Save metadata and artwork' }).click()
  const actions = meta.getByRole('group', { name: 'Metadata and artwork: actions' })
  const update = actions.getByRole('button', { name: 'Update Metadata' })
  await update.click()
  await expect(update.locator('svg')).toHaveAttribute('data-icon', 'tick')
  await actions.getByRole('button', { name: 'Refresh Metadata' }).click()
  const ask = page.getByRole('dialog', { name: 'Refresh metadata' })
  await expect(ask).toContainText('a game you matched by hand keeps its match')
  await ask.getByRole('button', { name: 'Cancel' }).click()
  await expect(ask).toHaveCount(0)
})

test('every tab keeps its main actions at its top (F11-S51)', async ({ page }) => {
  await page.goto('/settings/')
  for (const [tab, action] of [
    ['Library', 'Rescan ROMs folder'],
    ['Metadata and artwork', 'Update Metadata'],
    ['Tag suggestions', 'Propose franchise tags'],
    ['Transports and tools', 'Look for devices again'],
  ] as const) {
    await page.getByRole('tab', { name: tab }).click()
    const actions = page.getByRole('group', { name: `${tab}: actions` })
    await expect(actions.getByRole('button', { name: action })).toBeVisible()
    // a tab that sets nothing (Tag suggestions) has only its actions
    const fields = page
      .getByRole('region', { name: new RegExp(`^${tab}`) })
      .locator('input, select, button[aria-labelledby]')
    if ((await fields.count()) === 0) continue
    const top = await actions.boundingBox()
    const last = await fields.last().boundingBox()
    expect(top && last && top.y < last.y, `${tab}: the actions sit above the settings`).toBe(true)
  }
  await page.getByRole('tab', { name: 'Diagnostics' }).click()
  await expect(
    page
      .getByRole('group', { name: 'Diagnostics: actions' })
      .getByRole('link', { name: 'Export a support bundle' }),
  ).toBeVisible()
})

test('a running metadata pass stays in view after leaving the tab, beside the settings (F11-S53)', async ({
  page,
  request,
}) => {
  await page.setViewportSize({ width: 1500, height: 900 })
  await request.post('/__seed/metadata-running')
  await page.goto('/settings/#metadata')
  const ring = page.getByRole('progressbar', { name: 'Matching games' })
  await expect(ring).toHaveAttribute('aria-valuetext', 'Matching games: 10 of 40')
  await page.getByRole('link', { name: 'Devices' }).click()
  await page.getByRole('link', { name: 'Settings' }).click()
  await page.getByRole('tab', { name: 'Metadata and artwork' }).click()
  await expect(ring).toBeVisible()
  // the tracker uses the space to the right of the settings
  const tracker = await page.getByRole('region', { name: 'Metadata progress' }).boundingBox()
  const threshold = await page
    .getByRole('textbox', { name: 'Match acceptance threshold' })
    .boundingBox()
  expect(tracker && threshold && tracker.x > threshold.x + threshold.width).toBe(true)
  await page.getByRole('button', { name: 'Stop' }).click()
  await expect(ring).toHaveCount(0)
})
