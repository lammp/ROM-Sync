import type { Meta, StoryObj } from '@storybook/nextjs-vite'
import { expect } from 'storybook/test'
import { NoCover } from './NoCover'

const meta = {
  title: 'Atoms/NoCover',
  component: NoCover,
  args: { title: 'Earthworm Jim 3D' },
  decorators: [(Story) => <div style={{ width: 150 }}>{Story()}</div>],
} satisfies Meta<typeof NoCover>

export default meta
type Story = StoryObj<typeof meta>

export const Default: Story = {
  play: async ({ canvas }) => {
    await expect(canvas.getByText('Earthworm Jim 3D')).toBeVisible()
  },
}
export const LongTitle: Story = {
  args: {
    title: 'The Legend of Zelda: A Link to the Past & Four Swords (Europe) (En,Fr,De,Es,It)',
  },
}
