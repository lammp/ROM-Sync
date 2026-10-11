import { expect, test } from '@playwright/test'

test('the library opens from the exported bundle', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByRole('heading', { name: 'Library' })).toBeVisible()
  await expect(page).toHaveTitle('ROM-Sync')
})
