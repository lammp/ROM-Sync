import type { Meta, StoryObj } from '@storybook/nextjs-vite'
import { expect, fn } from 'storybook/test'
import { Select } from './Select'

const meta = {
  title: 'Atoms/Select',
  component: Select,
  args: {
    label: 'Sort',
    value: 'title',
    onChange: fn(),
    options: [
      { value: 'title', label: 'Title' },
      { value: 'year', label: 'Year' },
      { value: 'rating', label: 'Rating' },
    ],
  },
} satisfies Meta<typeof Select>

export default meta
type Story = StoryObj<typeof meta>

export const Default: Story = {
  play: async ({ canvas, args, userEvent }) => {
    await userEvent.selectOptions(canvas.getByRole('combobox', { name: 'Sort' }), 'year')
    await expect(args.onChange).toHaveBeenCalledWith('year')
  },
}

export const Chip: Story = {
  args: {
    label: 'Version',
    hideLabel: true,
    variant: 'chip',
    value: 'usa',
    options: [
      { value: 'usa', label: 'USA' },
      { value: 'eur', label: 'Europe' },
    ],
  },
}

export const Disabled: Story = { args: { disabled: true } }
