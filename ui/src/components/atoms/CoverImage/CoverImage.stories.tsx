import type { Meta, StoryObj } from '@storybook/nextjs-vite'
import { expect } from 'storybook/test'
import { CoverImage } from './CoverImage'

const COVER =
  'data:image/svg+xml;utf8,' +
  encodeURIComponent(
    '<svg xmlns="http://www.w3.org/2000/svg" width="300" height="400"><rect width="300" height="400"/></svg>',
  )

const meta = {
  title: 'Atoms/CoverImage',
  component: CoverImage,
  args: { src: COVER, alt: 'Super Metroid' },
  decorators: [(Story) => <div style={{ width: 150 }}>{Story()}</div>],
} satisfies Meta<typeof CoverImage>

export default meta
type Story = StoryObj<typeof meta>

export const Tile: Story = {
  play: async ({ canvas }) => {
    const img = canvas.getByRole('img', { name: 'Super Metroid' })
    await expect(img).toHaveAttribute('loading', 'lazy')
    await expect(img).toHaveAttribute('decoding', 'async')
  },
}
export const Big: Story = { args: { size: 'big' } }
export const Row: Story = { args: { size: 'row' } }
