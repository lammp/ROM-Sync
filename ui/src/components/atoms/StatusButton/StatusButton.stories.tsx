import type { Meta, StoryObj } from '@storybook/nextjs-vite'
import { expect, fn } from 'storybook/test'
import { StatusButton } from './StatusButton'

const meta = {
  title: 'Atoms/StatusButton',
  component: StatusButton,
  args: { label: 'Test connection', onClick: fn() },
} satisfies Meta<typeof StatusButton>

export default meta
type Story = StoryObj<typeof meta>

/** Not run yet: the recycle glyph and the words; a click runs it. */
export const Idle: Story = {
  play: async ({ canvas, args, userEvent }) => {
    await userEvent.click(canvas.getByRole('button', { name: 'Test connection' }))
    await expect(args.onClick).toHaveBeenCalledOnce()
  },
}

/** Running: the glyph turns, and the button waits and says it is busy. */
export const Running: Story = {
  args: { state: 'running' },
  play: async ({ canvas }) => {
    const button = canvas.getByRole('button', { name: 'Test connection' })
    await expect(button).toBeDisabled()
    await expect(button).toHaveAttribute('aria-busy', 'true')
  },
}

/** Passed: a tick. */
export const Passed: Story = { args: { state: 'passed' } }

/** Failed: a cross. */
export const Failed: Story = { args: { state: 'failed' } }

/** A tab's main action, larger, with a glyph of its own. */
export const Main: Story = {
  args: { label: 'Run Initial', icon: 'play', variant: 'primary', large: true },
}
