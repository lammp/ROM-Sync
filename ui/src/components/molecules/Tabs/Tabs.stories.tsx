import type { Meta, StoryObj } from '@storybook/nextjs-vite'
import { useState } from 'react'
import { expect, fn } from 'storybook/test'
import { Tabs, type TabsProps } from './Tabs'

function Bound(
  props: Omit<TabsProps, 'selected' | 'onSelect'> & { onSelect: (id: string) => void },
) {
  const [selected, setSelected] = useState(props.tabs[0]?.id ?? '')
  return (
    <Tabs
      {...props}
      selected={selected}
      onSelect={(id) => {
        setSelected(id)
        props.onSelect(id)
      }}
    />
  )
}

const meta = {
  title: 'Molecules/Tabs',
  component: Bound,
  args: {
    label: 'Settings',
    onSelect: fn(),
    tabs: [
      { id: 'library', label: 'Library', panel: <p>ROMs folder</p> },
      {
        id: 'metadata',
        label: 'Metadata and artwork',
        dirty: true,
        panel: <input aria-label="Client ID" />,
      },
      { id: 'diagnostics', label: 'Diagnostics', panel: <p>Version 2.0.0</p> },
    ],
  },
} satisfies Meta<typeof Bound>

export default meta
type Story = StoryObj<typeof meta>

/** One panel shown; a click shows another; the edited tab says so. */
export const Switching: Story = {
  play: async ({ canvas, args, userEvent }) => {
    await expect(canvas.getByRole('tab', { name: 'Library' })).toHaveAttribute(
      'aria-selected',
      'true',
    )
    await expect(canvas.getByRole('tabpanel', { name: 'Library' })).toHaveTextContent('ROMs folder')
    await expect(
      canvas.getByRole('tab', { name: 'Metadata and artwork, unsaved changes' }),
    ).toBeVisible()
    await userEvent.click(canvas.getByRole('tab', { name: 'Diagnostics' }))
    await expect(args.onSelect).toHaveBeenCalledWith('diagnostics')
    await expect(canvas.getByRole('tabpanel', { name: 'Diagnostics' })).toBeVisible()
    await expect(canvas.queryByText('ROMs folder')).not.toBeVisible()
  },
}

/** The arrow keys, Home and End move between tabs and wrap round. */
export const ByKeyboard: Story = {
  play: async ({ canvas, userEvent }) => {
    canvas.getByRole('tab', { name: 'Library' }).focus()
    await userEvent.keyboard('{ArrowLeft}')
    await expect(canvas.getByRole('tab', { name: 'Diagnostics' })).toHaveFocus()
    await expect(canvas.getByRole('tab', { name: 'Diagnostics' })).toHaveAttribute(
      'aria-selected',
      'true',
    )
    await userEvent.keyboard('{Home}')
    await expect(canvas.getByRole('tab', { name: 'Library' })).toHaveFocus()
    await userEvent.keyboard('{ArrowRight}')
    await expect(canvas.getByRole('tab', { name: /^Metadata/ })).toHaveAttribute(
      'aria-selected',
      'true',
    )
  },
}
