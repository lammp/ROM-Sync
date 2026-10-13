import { expect, test, type Page } from '@playwright/test'

// F11-S35: on every page, Tab alone reaches every control a pointer can use.
// Each control the page draws is marked, Tab is pressed until focus has gone
// round, and every mark must have held focus at least once.

const CONTROLS =
  'a[href], button, input, select, textarea, summary, [tabindex]:not([tabindex="-1"])'

/**
 * Every control the page draws, named by what it is and says, numbered among
 * its namesakes in document order. A name, not the DOM node, so a list that
 * redraws itself (the windowed grid) does not lose track of its controls.
 */
function marks(selector: string): { all: string[]; active: string } {
  const named = new Map<string, number>()
  const all: string[] = []
  let active = ''
  document.querySelectorAll<HTMLElement>(selector).forEach((el) => {
    const disabled = (el as HTMLButtonElement).disabled === true
    const hidden = el.closest('[hidden], [inert], [aria-hidden="true"]') !== null
    if (disabled || hidden || el.getClientRects().length === 0) return
    const name = `${el.tagName.toLowerCase()} ${(el.getAttribute('aria-label') ?? el.textContent ?? '').trim().slice(0, 48)}`
    const n = (named.get(name) ?? 0) + 1
    named.set(name, n)
    const mark = `${name} #${n}`
    all.push(mark)
    if (el === document.activeElement) active = mark
  })
  return { all, active }
}

async function controls(page: Page): Promise<string[]> {
  return (await page.evaluate(marks, CONTROLS)).all
}

async function reachedByTab(page: Page, count: number): Promise<Set<string>> {
  const reached = new Set<string>()
  await page.locator('body').focus()
  for (let i = 0; i < count * 2 + 20; i++) {
    await page.keyboard.press('Tab')
    const { active } = await page.evaluate(marks, CONTROLS)
    if (active) reached.add(active)
  }
  return reached
}

async function missedByTab(page: Page): Promise<string[]> {
  const all = await controls(page)
  expect(all.length).toBeGreaterThan(3)
  const reached = await reachedByTab(page, all.length)
  return all.filter((c) => !reached.has(c))
}

async function everyControlReachable(page: Page) {
  expect(await missedByTab(page)).toEqual([])
}

const PAGES: {
  name: string
  path: string
  ready: (page: Page) => Promise<void>
  seed?: string
  device?: boolean
}[] = [
  {
    name: 'library',
    path: '/',
    ready: (page) =>
      expect(page.getByRole('toolbar', { name: 'Library' })).toContainText('40 of 40'),
  },
  {
    name: 'library with a device and a game open',
    path: '/',
    device: true,
    ready: async (page) => {
      await expect(page.getByRole('group', { name: 'Selection for Thor' })).toContainText(
        'selected',
      )
      await page.getByRole('searchbox').fill('star quest')
      await page
        .getByRole('button', { name: /^Star Quest 1\b/ })
        .first()
        .click()
      await expect(page.getByRole('article', { name: 'Star Quest 1' })).toBeVisible()
    },
  },
  {
    name: 'devices',
    path: '/devices/',
    ready: (page) =>
      expect(page.getByRole('list', { name: 'Devices' }).getByRole('article')).toHaveCount(5),
  },
  {
    name: 'one device',
    path: '/devices/?id=dev-1',
    ready: (page) => expect(page.getByText(/Sync will/)).toBeVisible(),
  },
  {
    name: 'system files',
    path: '/system-files/',
    device: true,
    ready: (page) => expect(page.getByRole('navigation', { name: 'Systems' })).toBeVisible(),
  },
  {
    name: 'settings',
    path: '/settings/#data',
    ready: (page) => expect(page.getByRole('table', { name: 'Upkeep' })).toContainText('·'),
  },
  {
    name: 'recover',
    path: '/recover/',
    seed: 'recover',
    ready: (page) =>
      expect(page.getByRole('table', { name: 'On Thor, not in the store' })).toBeVisible(),
  },
]

test.beforeEach(async ({ request }) => {
  await request.post('/__reset')
})

for (const p of PAGES) {
  test(`all_controls_reachable: ${p.name}`, async ({ page, request }) => {
    if (p.seed) await request.post(`/__seed/${p.seed}`)
    if (p.device) {
      await page.goto('/')
      await page.getByRole('combobox', { name: 'Device' }).selectOption('dev-1')
    }
    await page.goto(p.path)
    await p.ready(page)
    await everyControlReachable(page)
  })
}

test('the check bites: a control taken out of the tab order is reported', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByRole('toolbar', { name: 'Library' })).toContainText('40 of 40')
  await page.evaluate(() => {
    const b = document.createElement('button')
    b.textContent = 'Unreachable'
    b.tabIndex = -1
    document.querySelector('header')?.append(b)
  })
  expect(await missedByTab(page)).toEqual(['button Unreachable #1'])
})
