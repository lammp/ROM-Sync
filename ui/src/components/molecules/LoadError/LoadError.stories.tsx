import type { Meta, StoryObj } from '@storybook/nextjs-vite'
import { expect, fn } from 'storybook/test'
import { LoadError } from './LoadError'

const meta = {
  title: 'Molecules/LoadError',
  component: LoadError,
  args: { what: 'the library', message: 'The engine did not answer.', onRetry: fn() },
} satisfies Meta<typeof LoadError>

export default meta
type Story = StoryObj<typeof meta>

export const Failed: Story = {
  play: async ({ canvas, args, userEvent }) => {
    await userEvent.click(canvas.getByRole('button', { name: 'Retry' }))
    await expect(args.onRetry).toHaveBeenCalled()
  },
}

export const Retrying: Story = { args: { retrying: true } }
