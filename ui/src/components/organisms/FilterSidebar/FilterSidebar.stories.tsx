import type { Meta, StoryObj } from '@storybook/nextjs-vite'
import { expect, fn } from 'storybook/test'
import { FACETS } from '../../../lib/facets/facets'
import { FilterSidebar, type FacetView } from './FilterSidebar'

const VALUES: Record<string, string[]> = {
  system: ['Super Nintendo', 'Game Boy Advance', 'Nintendo 64'],
  genre: ['Platform', 'Role-playing (RPG)', 'Racing'],
  franchise: ['Mario', 'Metroid'],
  theme: ['Fantasy', 'Science fiction'],
  mode: ['Single player', 'Multiplayer'],
  perspective: ['Side view', 'Third person'],
  tag: ['Favourites'],
  decade: ['1980s', '1990s', '2000s'],
  region: ['USA', 'Europe', 'Japan'],
}

const facets: FacetView[] = FACETS.map((facet) => ({
  facet,
  rows: (VALUES[facet] ?? []).map((label, i) => ({
    value: label,
    label,
    count: 40 - i * 7,
    chosen: facet === 'system' && i === 0,
  })),
  hidden: facet === 'genre' ? 12 : 0,
  less: false,
  collapsed: facet === 'decade',
}))

const range = (min: number, max: number, gap: number) => ({
  min,
  max,
  gap,
  value: { lo: min, hi: max },
  onChange: fn(),
  valueText: (v: number) => String(v),
  exact: {
    min: '',
    max: '',
    onMin: fn(),
    onMax: fn(),
    minPlaceholder: 'from',
    maxPlaceholder: 'to',
  },
})

const meta = {
  title: 'Organisms/FilterSidebar',
  component: FilterSidebar,
  args: {
    active: [{ key: 'system:snes', label: 'Super Nintendo', onRemove: fn() }],
    onClearAll: fn(),
    onSmart: fn(),
    rating: 0,
    onRating: fn(),
    facets,
    onToggle: fn(),
    onFold: fn(),
    onCollapse: fn(),
    onClear: fn(),
    size: range(0, 1000, 10),
    year: range(1975, 2026, 0),
    flags: { matched: false, selected: false, ondevice: false, folder: false },
    onFlag: fn(),
    device: true,
  },
  decorators: [
    (Story) => (
      <div style={{ width: 260, background: 'var(--bg2)', padding: '10px 12px' }}>{Story()}</div>
    ),
  ],
} satisfies Meta<typeof FilterSidebar>

export default meta
type Story = StoryObj<typeof meta>

export const Default: Story = {
  play: async ({ canvas, args, userEvent }) => {
    await userEvent.click(canvas.getByRole('button', { name: /^Metroid/ }))
    await expect(args.onToggle).toHaveBeenCalledWith('franchise', 'Metroid')
    await userEvent.click(canvas.getByRole('button', { name: 'Top rated' }))
    await expect(args.onSmart).toHaveBeenCalledWith('rating>85 votes>50')
    await userEvent.click(canvas.getByRole('button', { name: 'Decade' }))
    await expect(args.onCollapse).toHaveBeenCalledWith('decade', false)
  },
}

export const NoDevice: Story = { args: { device: false, active: [] } }
