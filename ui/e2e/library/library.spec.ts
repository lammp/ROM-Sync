import { expect, test } from '@playwright/test'

// Each spec starts from the same invented library: forty games, one device.
test.beforeEach(async ({ request }) => {
  await request.post('/__reset')
})

test('the library opens from the exported bundle with every game listed', async ({ page }) => {
  await page.goto('/')
  await expect(page).toHaveTitle('ROM-Sync')
  await expect(page.getByRole('link', { name: 'Library' })).toHaveAttribute('aria-current', 'page')
  await expect(page.getByRole('toolbar', { name: 'Library' })).toContainText('40 of 40')
})

test('a search and a facet narrow the grid, and a chip clears the facet', async ({ page }) => {
  await page.goto('/')
  await page.getByRole('searchbox').fill('galaxy')
  const toolbar = page.getByRole('toolbar', { name: 'Library' })
  await expect(toolbar).not.toContainText('40 of 40')
  await page.getByRole('searchbox').fill('')
  await page.getByRole('button', { name: /^Nintendo 64 ?\d+$/ }).click()
  await expect(toolbar).toContainText('10 of 40')
  await page
    .getByRole('group', { name: 'Filters in force' })
    .getByRole('button', { name: /Nintendo 64/ })
    .click()
  await expect(toolbar).toContainText('40 of 40')
})

test('choosing the device shows its selection, and a badge changes it through the engine', async ({
  page,
}) => {
  await page.goto('/')
  await page.getByRole('combobox', { name: 'Device' }).selectOption('dev-1')
  const summary = page.getByRole('group', { name: 'Selection for Thor' })
  await expect(summary).toContainText('11 selected')
  // The grid is windowed: a search brings the game into view.
  await page.getByRole('searchbox').fill('star quest')
  await page.getByRole('button', { name: 'Star Quest 1 for Thor: selected' }).click()
  await expect(summary).toContainText('10 selected')
  await page.reload()
  await expect(page.getByRole('combobox', { name: 'Device' })).toHaveValue('dev-1')
  await expect(page.getByRole('group', { name: 'Selection for Thor' })).toContainText('10 selected')
})

test('a game opens in the detail panel and closes again', async ({ page }) => {
  await page.goto('/')
  await page.getByRole('searchbox').fill('star quest')
  await page
    .getByRole('button', { name: /^Star Quest 1\b/ })
    .first()
    .click()
  const panel = page.getByRole('article', { name: 'Star Quest 1' })
  await expect(panel).toContainText('Space opera')
  await panel.getByRole('button', { name: 'Close details' }).click()
  await expect(panel).toBeHidden()
})
