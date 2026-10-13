import type { Meta, StoryObj } from '@storybook/nextjs-vite'
import { expect, fn } from 'storybook/test'
import { SearchInput } from './SearchInput'

const meta = {
  title: 'Atoms/SearchInput',
  component: SearchInput,
  args: { value: '', onChange: fn() },
} satisfies Meta<typeof SearchInput>

export default meta
type Story = StoryObj<typeof meta>

export const Empty: Story = {
  play: async ({ canvas, args, userEvent }) => {
    await userEvent.type(canvas.getByRole('searchbox', { name: 'Search the library' }), 'z')
    await expect(args.onChange).toHaveBeenLastCalledWith('z')
  },
}

export const WithQuery: Story = { args: { value: 'system:snes rating>=80' } }
