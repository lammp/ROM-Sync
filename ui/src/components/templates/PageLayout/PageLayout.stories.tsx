import type { Meta, StoryObj } from '@storybook/nextjs-vite'
import { expect } from 'storybook/test'
import { Button } from '../../atoms/Button/Button'
import { PageLayout } from './PageLayout'

const meta = {
  title: 'Templates/PageLayout',
  component: PageLayout,
  args: { heading: 'Devices', children: <p>Two devices.</p> },
  decorators: [(Story) => <div style={{ height: 240, display: 'flex' }}>{Story()}</div>],
} satisfies Meta<typeof PageLayout>

export default meta
type Story = StoryObj<typeof meta>

export const Default: Story = {
  play: async ({ canvas }) => {
    await expect(canvas.getByRole('heading', { level: 1, name: 'Devices' })).toBeVisible()
  },
}

export const WithActions: Story = { args: { actions: <Button>Refresh</Button> } }
