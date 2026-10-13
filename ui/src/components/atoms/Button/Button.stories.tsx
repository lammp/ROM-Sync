import type { Meta, StoryObj } from '@storybook/nextjs-vite'
import { expect, fn } from 'storybook/test'
import { SURFACES, parse } from '../../../design/contrast/contrast'
import { COLOUR } from '../../../design/tokens/tokens'
import { Button } from './Button'

const meta = {
  title: 'Atoms/Button',
  component: Button,
  args: { children: 'Scan library', onClick: fn() },
} satisfies Meta<typeof Button>

export default meta
type Story = StoryObj<typeof meta>

export const Default: Story = {
  play: async ({ canvas, args, userEvent }) => {
    await userEvent.click(canvas.getByRole('button', { name: 'Scan library' }))
    await expect(args.onClick).toHaveBeenCalledOnce()
  },
}

export const Primary: Story = { args: { variant: 'primary', children: 'Sync now' } }

export const Danger: Story = { args: { variant: 'danger', children: 'Remove profile' } }

export const Active: Story = {
  args: { active: true, children: 'Grid' },
  play: async ({ canvas }) => {
    await expect(canvas.getByRole('button', { name: 'Grid', pressed: true })).toBeVisible()
  },
}

export const Small: Story = { args: { small: true, children: 'Accept' } }

/** A tab's main action, larger at its top (F11-S51). */
export const Large: Story = { args: { large: true, variant: 'primary', children: 'Run Initial' } }

export const Disabled: Story = {
  args: { disabled: true, children: 'Not connected' },
  play: async ({ canvas }) => {
    await expect(canvas.getByRole('button', { name: 'Not connected' })).toBeDisabled()
  },
}

/** F11-S9: the ring is drawn, 2 px wide and 2 px off, in --focus, on every surface. */
export const FocusRing: Story = {
  render: (args) => (
    <div>
      {SURFACES.map((surface) => (
        <div key={surface} style={{ background: `var(${surface})`, padding: 8 }}>
          <Button {...args} variant="primary">
            {surface}
          </Button>
        </div>
      ))}
    </div>
  ),
  play: async ({ canvas, userEvent }) => {
    const { r, g, b } = parse(COLOUR['--focus'])
    for (const surface of SURFACES) {
      await userEvent.tab()
      const button = canvas.getByRole('button', { name: surface })
      await expect(button).toHaveFocus()
      const style = getComputedStyle(button)
      await expect([style.outlineStyle, style.outlineWidth, style.outlineOffset]).toEqual([
        'solid',
        '2px',
        '2px',
      ])
      await expect(style.outlineColor.match(/\d+/g)?.map(Number)).toEqual([r, g, b])
    }
  },
}
