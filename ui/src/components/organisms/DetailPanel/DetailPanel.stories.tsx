import type { Meta, StoryObj } from '@storybook/nextjs-vite'
import { expect, fn } from 'storybook/test'
import { JobLine } from '../../molecules/JobLine/JobLine'
import { DetailPanel, type DetailGame } from './DetailPanel'

const game: DetailGame = {
  id: 7,
  title: 'Super Metroid',
  name: 'snes/Super Metroid (Japan, USA) (En,Ja).sfc',
  cover: null,
  year: 1994,
  rating: 93.4,
  votes: 412,
  size: 3 * 2 ** 20,
  kind: 'file',
  files: 1,
  regions: ['Japan', 'USA'],
  summary: 'Samus returns to Zebes to recover the last Metroid.',
  matched: true,
  igdbName: 'Super Metroid',
  confidence: 0.97,
  genres: ['Platform', 'Adventure'],
}

const meta = {
  title: 'Organisms/DetailPanel',
  component: DetailPanel,
  args: {
    game,
    versions: [{ id: 7, sysLabel: 'Super Nintendo', year: 1994, selected: true, loose: false }],
    onPickVersion: fn(),
    device: { name: 'Thor', selected: true, onToggle: fn() },
    tags: [
      { tag: 'Metroid', kind: 'franchise', state: 'accepted' },
      { tag: 'Metroidvania', kind: 'user', state: 'proposed' },
    ],
    onRemoveTag: fn(),
    onDecideTag: fn(),
    onAddTag: fn(),
    onRematch: fn(),
    onClose: fn(),
  },
  decorators: [
    (Story) => <div style={{ width: 420, background: 'var(--bg2)', padding: 16 }}>{Story()}</div>,
  ],
} satisfies Meta<typeof DetailPanel>

export default meta
type Story = StoryObj<typeof meta>

export const Matched: Story = {
  play: async ({ canvas, args, userEvent }) => {
    await expect(canvas.getByRole('heading', { level: 2, name: 'Super Metroid' })).toBeVisible()
    await userEvent.click(canvas.getByRole('button', { name: '✓ Selected for Thor' }))
    await expect(args.device?.onToggle).toHaveBeenCalledOnce()
    await userEvent.type(canvas.getByRole('textbox', { name: /Wrong match/ }), '1103{Enter}')
    await expect(args.onRematch).toHaveBeenCalledWith('1103')
  },
}

export const Unmatched: Story = {
  args: {
    game: {
      ...game,
      matched: false,
      summary: null,
      igdbName: null,
      rating: null,
      votes: null,
      year: null,
    },
    device: undefined,
    tags: [],
    rematch: (
      <JobLine state="running" progress={{ phase: 'matching', done: 0, total: 1, current: null }} />
    ),
  },
}

export const Folder: Story = {
  args: { game: { ...game, kind: 'folder', files: 2, title: 'Okami', name: 'ps2/Okami (USA)' } },
}
