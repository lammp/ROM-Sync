import type { Meta, StoryObj } from '@storybook/nextjs-vite'
import { expect, fn } from 'storybook/test'
import { SetupSteps } from './SetupSteps'

const meta = {
  title: 'Organisms/SetupSteps',
  component: SetupSteps,
  args: {
    steps: [
      {
        label: '1. Point at your ROMs folder',
        done: true,
        action: { label: 'Go to Library', onClick: fn() },
      },
      {
        label: '2. Read the library',
        done: false,
        action: { label: 'Rescan store', onClick: fn() },
      },
      {
        label: '3. Add IGDB credentials for covers and details',
        done: false,
        action: { label: 'Go to Metadata', onClick: fn() },
        note: 'libretro box art needs no account.',
      },
    ],
    onDismiss: fn(),
  },
} satisfies Meta<typeof SetupSteps>

export default meta
type Story = StoryObj<typeof meta>

export const Incomplete: Story = {
  play: async ({ canvas, args, userEvent }) => {
    await userEvent.click(canvas.getByRole('button', { name: 'Rescan store' }))
    await expect(args.steps[1]?.action.onClick).toHaveBeenCalled()
  },
}

export const Complete: Story = {
  args: {
    steps: [
      {
        label: '1. Point at your ROMs folder',
        done: true,
        action: { label: 'Go to Library', onClick: fn() },
      },
    ],
  },
}
