import { expect, test } from '@playwright/test'

test.beforeEach(async ({ request }) => {
  await request.post('/__reset')
})

test('the device page is a search parameter: Contents opens it from the list', async ({ page }) => {
  await page.goto('/devices/')
  await page
    .getByRole('article', { name: 'Thor' })
    .getByRole('button', { name: 'Contents' })
    .click()
  await expect(page).toHaveURL(/\/devices\/?\?id=dev-1$/)
  await expect(page.getByRole('heading', { name: /^Thor/ })).toBeVisible()
  await expect(page.getByRole('table', { name: 'Systems' })).toBeVisible()
  await expect(page.getByText(/Sync will/)).toContainText('send 10')
  await expect(page.getByRole('table', { name: 'History' })).toContainText('no runs yet')
})

test('a sync is asked, runs, is said, and lands in the history and the plan', async ({ page }) => {
  await page.goto('/devices/?id=dev-1')
  await page.getByRole('button', { name: 'Sync', exact: true }).click()
  const dialog = page.getByRole('dialog', { name: 'Sync Thor' })
  await expect(dialog.getByRole('table')).toContainText('Send')
  await dialog.getByRole('button', { name: 'Start' }).click()
  await expect(page.getByText(/^Thor synced: sent 10, removed 0/)).toBeVisible()
  await expect(page.getByRole('table', { name: 'History' })).toContainText('#1')
  await expect(page.getByText('the device matches your selection')).toBeVisible()
})

test('a system set to none plans the removal of what it holds', async ({ page }) => {
  await page.goto('/devices/?id=dev-1')
  const snes = page.getByRole('radiogroup', { name: 'Selection for Super Nintendo' })
  await snes.getByRole('radio', { name: 'none' }).click()
  await expect(snes.getByRole('radio', { name: 'none' })).toHaveAttribute('aria-checked', 'true')
  await expect(page.getByText(/Sync will/)).toContainText('remove 1')
})

test('an unknown device says so', async ({ page }) => {
  await page.goto('/devices/?id=dev-404')
  await expect(page.getByRole('heading', { name: 'Device not found' })).toBeVisible()
})
