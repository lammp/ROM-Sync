import type { Meta, StoryObj } from '@storybook/nextjs-vite'
import { expect } from 'storybook/test'
import { useEngine } from '../../../queries/engine/engine'
import { Providers } from './Providers'

function Probe() {
  const engine = useEngine()
  return <p>engine polls every {engine.pollMs} ms</p>
}

const meta = {
  title: 'Features/Shell/Providers',
  component: Providers,
  args: { children: <Probe /> },
} satisfies Meta<typeof Providers>

export default meta
type Story = StoryObj<typeof meta>

export const Default: Story = {
  play: async ({ canvas }) => {
    await expect(canvas.getByText('engine polls every 1000 ms')).toBeVisible()
  },
}
