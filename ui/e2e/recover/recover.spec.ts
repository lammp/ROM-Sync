import { expect, test } from '@playwright/test'

test.beforeEach(async ({ request }) => {
  await request.post('/__reset')
})

test('there is no Recover in the views when nothing needs recovering', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByRole('link', { name: 'Devices' })).toBeVisible()
  await expect(page.getByRole('combobox', { name: 'Device' })).toContainText('Thor')
  await expect(page.getByRole('link', { name: 'Recover' })).toHaveCount(0)
})

test('Recover appears when a device holds what the store lacks, and says what the next sync does', async ({
  page,
  request,
}) => {
  await request.post('/__seed/recover')
  await page.goto('/')
  await page.getByRole('link', { name: 'Recover' }).click()
  await expect(page).toHaveURL(/\/recover\/?$/)
  const table = page.getByRole('table', { name: 'On Thor, not in the store' })
  await expect(table.getByRole('row')).toHaveCount(5)
  await expect(table).toContainText('not in the store, so the next sync removes it from the device')
  await expect(table).toContainText('left alone: nes is not a store system')
})

test('a recovered file is placed in the store, read into the library, and leaves the list', async ({
  page,
  request,
}) => {
  await request.post('/__seed/recover')
  await page.goto('/recover/')
  await page.getByRole('button', { name: 'Recover Hidden Gem (USA).sfc' }).click()
  await expect(page.getByText('Hidden Gem (USA).sfc is in the library')).toBeVisible()
  await expect(page.getByRole('table', { name: 'On Thor, not in the store' })).not.toContainText(
    'Hidden Gem',
  )
  await page.getByRole('link', { name: 'Library' }).click()
  await page.getByRole('searchbox').fill('hidden gem')
  // The rescan also reads in the clashing file that was already in the store's folder.
  await expect(page.getByRole('toolbar', { name: 'Library' })).toContainText('1 of 42')
})

test('a name the store already has is refused and nothing is replaced', async ({
  page,
  request,
}) => {
  await request.post('/__seed/recover')
  await page.goto('/recover/')
  await page.getByRole('button', { name: 'Recover Clash (USA).sfc' }).click()
  await expect(page.getByText('the store already has this name')).toBeVisible()
})
