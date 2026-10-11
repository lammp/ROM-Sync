import type { Meta, StoryObj } from '@storybook/nextjs-vite'
import { expect } from 'storybook/test'
import { PlanDetailList } from './PlanDetailList'

const meta = {
  title: 'Molecules/PlanDetailList',
  component: PlanDetailList,
  args: {
    items: [
      { action: 'send', system: 'snes', name: 'Super Metroid.sfc', size: 3 * 2 ** 20 },
      { action: 'update', system: 'gba', name: 'Metroid Fusion.gba', size: 8 * 2 ** 20 },
      { action: 'remove', system: 'nes', name: 'Metroid.nes', size: 2 ** 17 },
    ],
  },
} satisfies Meta<typeof PlanDetailList>

export default meta
type Story = StoryObj<typeof meta>

export const Three: Story = {
  play: async ({ canvas }) => {
    await expect(canvas.getAllByRole('listitem')).toHaveLength(3)
  },
}
