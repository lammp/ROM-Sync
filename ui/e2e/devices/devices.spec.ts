import { expect, test } from '@playwright/test'

test.beforeEach(async ({ request }) => {
  await request.post('/__reset')
})

test('the devices page lists every profile and every device plugged in without one', async ({
  page,
}) => {
  await page.goto('/devices/')
  await expect(page.getByRole('heading', { name: 'Devices' })).toBeVisible()
  await expect(page.getByRole('link', { name: 'Devices' })).toHaveAttribute('aria-current', 'page')
  const list = page.getByRole('list', { name: 'Devices' })
  await expect(list.getByRole('article')).toHaveCount(5)
  await expect(page.getByRole('article', { name: 'Thor' })).toContainText('online · ADB')
  await expect(page.getByRole('article', { name: 'Deck card' })).toContainText('offline')
  await expect(page.getByRole('article', { name: 'Android device (serial-3)' })).toContainText(
    'accept the debugging prompt on the device',
  )
})

test('a new profile is made for a drive through the dialog', async ({ page }) => {
  await page.goto('/devices/')
  await page
    .getByRole('article', { name: 'SD card (E:)' })
    .getByRole('button', { name: 'New profile…' })
    .click()
  const dialog = page.getByRole('dialog', { name: 'New device profile' })
  await dialog.getByRole('textbox', { name: 'Name' }).fill('Card')
  await dialog.getByRole('button', { name: 'Create' }).click()
  await expect(page).toHaveURL(/\/devices\/?\?id=dev-3$/)
  await expect(page.getByRole('status')).toContainText('Profile Card created')
})

test('Choose games takes the device to the library', async ({ page }) => {
  await page.goto('/devices/')
  await page
    .getByRole('article', { name: 'Thor' })
    .getByRole('button', { name: 'Choose games' })
    .click()
  await expect(page).toHaveURL(/\/$/)
  await expect(page.getByRole('combobox', { name: 'Device' })).toHaveValue('dev-1')
  await expect(page.getByRole('group', { name: 'Selection for Thor' })).toContainText('11 selected')
})
