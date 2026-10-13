import type { Meta, StoryObj } from '@storybook/nextjs-vite'
import { expect, fn } from 'storybook/test'
import { ReloadButton } from './ReloadButton'

const meta = {
  title: 'Atoms/ReloadButton',
  component: ReloadButton,
  args: { label: 'Look for devices again', onClick: fn() },
} satisfies Meta<typeof ReloadButton>

export default meta
type Story = StoryObj<typeof meta>

/** An icon named by what it reads again; a click asks. */
export const Ready: Story = {
  play: async ({ canvas, args, userEvent }) => {
    const button = canvas.getByRole('button', { name: 'Look for devices again' })
    await expect(button).toHaveAttribute('title', 'Look for devices again')
    await expect(button).toHaveTextContent('')
    await userEvent.click(button)
    await expect(args.onClick).toHaveBeenCalledOnce()
  },
}

/** Reading now: it waits, and says it is busy. */
export const Busy: Story = {
  args: { busy: true },
  play: async ({ canvas }) => {
    const button = canvas.getByRole('button', { name: 'Look for devices again' })
    await expect(button).toBeDisabled()
    await expect(button).toHaveAttribute('aria-busy', 'true')
  },
}
