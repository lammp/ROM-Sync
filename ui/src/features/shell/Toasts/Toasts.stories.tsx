import type { Meta, StoryObj } from '@storybook/nextjs-vite'
import { expect, waitFor } from 'storybook/test'
import { appStore } from '../../../store/store'
import { Toasts } from './Toasts'

const meta = {
  title: 'Features/Shell/Toasts',
  component: Toasts,
} satisfies Meta<typeof Toasts>

export default meta
type Story = StoryObj<typeof meta>

export const FromTheStore: Story = {
  play: async ({ canvas }) => {
    appStore.getState().ui.toast('Thor synced: sent 3')
    await waitFor(() => expect(canvas.getByRole('status')).toHaveTextContent('Thor synced: sent 3'))
  },
}
