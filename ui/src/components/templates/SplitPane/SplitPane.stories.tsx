import type { Meta, StoryObj } from '@storybook/nextjs-vite'
import { expect } from 'storybook/test'
import { SplitPane } from './SplitPane'

const meta = {
  title: 'Templates/SplitPane',
  component: SplitPane,
  args: { listLabel: 'Systems', list: <p>PlayStation</p>, children: <p>BIOS files</p> },
} satisfies Meta<typeof SplitPane>

export default meta
type Story = StoryObj<typeof meta>

export const Default: Story = {
  play: async ({ canvas }) => {
    await expect(canvas.getByRole('navigation', { name: 'Systems' })).toHaveTextContent(
      'PlayStation',
    )
  },
}
