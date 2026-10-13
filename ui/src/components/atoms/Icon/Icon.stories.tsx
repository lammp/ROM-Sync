import type { Meta, StoryObj } from '@storybook/nextjs-vite'
import { expect } from 'storybook/test'
import { ICONS, Icon } from './Icon'

const meta = {
  title: 'Atoms/Icon',
  component: Icon,
  args: { name: 'edit' },
} satisfies Meta<typeof Icon>

export default meta
type Story = StoryObj<typeof meta>

/** One glyph, hidden from assistive technology: the button or words beside it name it. */
export const Edit: Story = {
  play: async ({ canvasElement }) => {
    const svg = canvasElement.querySelector('svg')
    await expect(svg).toHaveAttribute('aria-hidden', 'true')
    await expect(svg).toHaveAttribute('data-icon', 'edit')
  },
}

/** Work under way: the recycle glyph turns. */
export const Turning: Story = { args: { name: 'recycle', turning: true } }

/** Every glyph there is, each beside its name. */
export const All: Story = {
  render: () => (
    <span>
      {ICONS.map((name) => (
        <span key={name}>
          <Icon name={name} /> {name}{' '}
        </span>
      ))}
    </span>
  ),
  play: async ({ canvasElement }) => {
    await expect(canvasElement.querySelectorAll('svg')).toHaveLength(ICONS.length)
  },
}
