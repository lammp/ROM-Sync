import type { Meta, StoryObj } from '@storybook/nextjs-vite'
import { expect, waitFor } from 'storybook/test'
import { GameTile } from '../../molecules/GameTile/GameTile'
import { VirtualGameGrid } from './VirtualGameGrid'

type Box = { id: number }
const boxes: Box[] = Array.from({ length: 1000 }, (_, i) => ({ id: i }))

const meta = {
  title: 'Organisms/VirtualGameGrid',
  component: VirtualGameGrid<Box>,
  args: {
    items: boxes,
    itemKey: (b: Box) => b.id,
    renderItem: (b: Box) => (
      <div style={{ height: 200, background: 'var(--bg2)' }}>item {b.id}</div>
    ),
    view: 'grid',
    tile: 150,
    layoutKey: 'boxes',
    label: 'Games',
  },
  // 1032 px wide with the grid's 16 px side padding leaves the 1000 px the
  // version 1 capture measured; 600 px of viewport, as captured.
  decorators: [
    (Story) => <div style={{ width: 1032, height: 600, display: 'flex' }}>{Story()}</div>,
  ],
} satisfies Meta<typeof VirtualGameGrid<Box>>

export default meta
type Story = StoryObj<typeof meta>

const rendered = (root: HTMLElement) => root.querySelectorAll('li').length
const inner = (root: HTMLElement) => root.querySelector('ul') as HTMLElement

/** The capture's "a thousand games" and "a long scroll moves the window", measured in Chromium. */
export const WindowMatchesFixture: Story = {
  play: async ({ canvasElement, canvas }) => {
    await waitFor(() => expect(rendered(canvasElement)).toBe(30))
    const ul = inner(canvasElement)
    await expect(ul.style.height).toBe('35738px')
    await expect(ul.style.paddingTop).toBe('0px')
    await expect(ul.style.gridTemplateColumns).toMatch(/^repeat\(6, minmax\(0(px)?, 1fr\)\)$/)
    const scroller = canvas.getByRole('region', { name: 'Games' })
    scroller.scrollTop = 2000
    scroller.dispatchEvent(new Event('scroll'))
    await waitFor(() => expect(ul.style.paddingTop).toBe('1498px'))
    await expect(rendered(canvasElement)).toBe(48)
    await expect(canvas.getByText('item 42')).toBeVisible()
  },
}

export const List: Story = {
  args: { view: 'list', renderItem: (b: Box) => <div style={{ height: 32 }}>row {b.id}</div> },
  play: async ({ canvasElement }) => {
    await waitFor(() => expect(rendered(canvasElement)).toBe(21))
  },
}

export const Empty: Story = {
  args: { items: [], empty: 'Nothing matches these filters.' },
  play: async ({ canvas }) => {
    await expect(canvas.getByText('Nothing matches these filters.')).toBeVisible()
  },
}

const games = Array.from({ length: 200 }, (_, i) => ({
  id: i,
  title: `Game ${i + 1}`,
  name: `game-${i + 1}.sfc`,
  system: 'snes',
  year: 1990 + (i % 10),
  rating: 60 + (i % 40),
  cover: null,
}))

export const Tiles: Story = {
  args: {
    items: games as unknown as Box[],
    renderItem: (g: Box) => (
      <GameTile
        game={g as unknown as (typeof games)[number]}
        current={false}
        onOpen={() => undefined}
      />
    ),
  },
  play: async ({ canvasElement }) => {
    await waitFor(() => expect(rendered(canvasElement)).toBeGreaterThan(0))
    await expect(rendered(canvasElement)).toBeLessThan(games.length)
  },
}
