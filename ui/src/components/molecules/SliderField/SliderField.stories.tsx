import type { Meta, StoryObj } from '@storybook/nextjs-vite'
import { useState } from 'react'
import { expect, fn } from 'storybook/test'
import { SliderField } from './SliderField'

const meta = {
  title: 'Molecules/SliderField',
  component: SliderField,
  args: {
    label: 'Match acceptance threshold',
    value: '0.55',
    onChange: fn(),
    min: 0,
    max: 1,
    step: 0.01,
    help: 'A candidate scoring at least this is accepted.',
  },
} satisfies Meta<typeof SliderField>

export default meta
type Story = StoryObj<typeof meta>

/** A scale from 0 to 1, with its number to the left to fine-tune. */
export const Threshold: Story = {
  play: async ({ canvas }) => {
    await expect(canvas.getByRole('textbox', { name: 'Match acceptance threshold' })).toHaveValue(
      '0.55',
    )
    await expect(
      canvas.getByRole('slider', { name: 'Match acceptance threshold, scale' }),
    ).toHaveValue('0.55')
  },
}

/** Whole steps with a unit: errors in a row, from 1 to 100. */
export const Count: Story = {
  args: { label: 'Stop after this many failures in a row', value: '25', min: 1, max: 100, step: 1 },
}

/** Typing and dragging move each other. */
export const Linked: Story = {
  render: function Render(args) {
    const [value, setValue] = useState(args.value)
    return <SliderField {...args} value={value} onChange={setValue} />
  },
  play: async ({ canvas, userEvent }) => {
    const box = canvas.getByRole('textbox', { name: 'Match acceptance threshold' })
    await userEvent.clear(box)
    await userEvent.type(box, '0.7')
    await expect(
      canvas.getByRole('slider', { name: 'Match acceptance threshold, scale' }),
    ).toHaveValue('0.7')
  },
}

/** A number past the bounds is said; the scale rests at its end. */
export const Refused: Story = { args: { value: '2', error: 'At most 1' } }
