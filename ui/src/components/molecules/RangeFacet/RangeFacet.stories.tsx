import type { Meta, StoryObj } from '@storybook/nextjs-vite'
import { useState } from 'react'
import { expect, fireEvent, fn } from 'storybook/test'
import { RangeFacet, type Pair } from './RangeFacet'

const exact = (min = '', max = '') => ({
  min,
  max,
  onMin: fn(),
  onMax: fn(),
  minPlaceholder: 'from',
  maxPlaceholder: 'to',
})

const meta = {
  title: 'Molecules/RangeFacet',
  component: RangeFacet,
  args: {
    title: 'Year',
    min: 1975,
    max: 2026,
    gap: 0,
    value: { lo: 1975, hi: 2026 },
    onChange: fn(),
    valueText: (v: number) => String(v),
    exact: exact(),
  },
  decorators: [
    (Story) => <div style={{ background: 'var(--bg2)', padding: 12, width: 260 }}>{Story()}</div>,
  ],
} satisfies Meta<typeof RangeFacet>

export default meta
type Story = StoryObj<typeof meta>

/** Held state, so a story behaves as the sidebar does. */
function Held(args: Story['args'] & { value: Pair }) {
  const [value, setValue] = useState(args.value)
  return (
    <RangeFacet
      {...(args as Parameters<typeof RangeFacet>[0])}
      value={value}
      onChange={(p) => {
        setValue(p)
        args.onChange?.(p)
      }}
    />
  )
}

export const Year: Story = {
  render: (args) => <Held {...args} />,
  play: async ({ canvas, args }) => {
    const lo = canvas.getByRole('slider', { name: 'Year, lower bound' })
    const hi = canvas.getByRole('slider', { name: 'Year, upper bound' })
    fireEvent.change(hi, { target: { value: '1990' } })
    fireEvent.change(lo, { target: { value: '2000' } })
    await expect(args.onChange).toHaveBeenLastCalledWith({ lo: 1990, hi: 1990 })
  },
}

export const Size: Story = {
  args: {
    title: 'Size',
    min: 0,
    max: 1000,
    gap: 10,
    value: { lo: 0, hi: 1000 },
    valueText: (v: number) => (v <= 0 || v >= 1000 ? 'no limit' : `step ${v}`),
    exact: { ...exact(), minPlaceholder: 'min e.g. 10mb', maxPlaceholder: 'max e.g. 2gb' },
  },
  render: (args) => <Held {...args} />,
  play: async ({ canvas, args }) => {
    fireEvent.change(canvas.getByRole('slider', { name: 'Size, upper bound' }), {
      target: { value: '500' },
    })
    fireEvent.change(canvas.getByRole('slider', { name: 'Size, lower bound' }), {
      target: { value: '499' },
    })
    await expect(args.onChange).toHaveBeenLastCalledWith({ lo: 490, hi: 500 })
  },
}

export const TypedBound: Story = {
  args: { exact: exact('1990', '') },
  play: async ({ canvas, args, userEvent }) => {
    const from = canvas.getByRole('textbox', { name: 'Year, from' })
    await expect(from).toHaveValue('1990')
    await userEvent.clear(from)
    await userEvent.type(from, '1985{Enter}')
    await expect(args.exact.onMin).toHaveBeenCalledWith('1985')
  },
}
