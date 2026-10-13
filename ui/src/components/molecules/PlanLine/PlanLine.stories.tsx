import type { Meta, StoryObj } from '@storybook/nextjs-vite'
import { expect } from 'storybook/test'
import { PlanLine, type PlanSummary } from './PlanLine'

const MB = 2 ** 20
const plan: PlanSummary = {
  send: [
    { system: 'snes', name: 'Super Metroid.sfc', size: 3 * MB },
    { system: 'gba', name: 'Metroid Fusion.gba', size: 8 * MB },
  ],
  update: [],
  remove: [{ system: 'nes', name: 'Metroid.nes', size: MB / 8 }],
  unchanged: 1190,
  unknownSystems: { pico8: 12 },
  bytes: { net: 11 * MB - MB / 8, free: 40 * 1024 * MB, fits: true },
}

const meta = {
  title: 'Molecules/PlanLine',
  component: PlanLine,
  args: { plan, list: <div>the full list</div> },
  decorators: [
    (Story) => <div style={{ background: 'var(--bg)', padding: 12, width: 640 }}>{Story()}</div>,
  ],
} satisfies Meta<typeof PlanLine>

export default meta
type Story = StoryObj<typeof meta>

export const Changes: Story = {
  play: async ({ canvas, userEvent }) => {
    await expect(canvas.getByText(/already in place/)).toHaveTextContent(
      'Sync will send 2 (11.0 MB), remove 1 (128.0 KB) · 1,190 already in place',
    )
    await userEvent.click(canvas.getByRole('button', { name: 'show list' }))
    await expect(canvas.getByText('the full list')).toBeVisible()
  },
}

export const InStep: Story = {
  args: {
    plan: {
      ...plan,
      send: [],
      remove: [],
      unknownSystems: {},
      bytes: { net: 0, free: null, fits: null },
    },
  },
  play: async ({ canvas }) => {
    await expect(canvas.getByText('the device matches your selection')).toBeVisible()
    await expect(canvas.queryByRole('button')).toBeNull()
  },
}

export const DoesNotFit: Story = {
  args: { plan: { ...plan, bytes: { ...plan.bytes, fits: false } } },
}
