import type { Meta, StoryObj } from '@storybook/nextjs-vite'
import { expect } from 'storybook/test'
import { LibraryLayout } from './LibraryLayout'

const meta = {
  title: 'Templates/LibraryLayout',
  component: LibraryLayout,
  args: { sidebar: <p>filters</p>, children: <p style={{ padding: 16 }}>grid</p> },
  decorators: [(Story) => <div style={{ height: 320, display: 'flex' }}>{Story()}</div>],
} satisfies Meta<typeof LibraryLayout>

export default meta
type Story = StoryObj<typeof meta>

export const WithoutPanel: Story = {
  play: async ({ canvas }) => {
    await expect(canvas.getByRole('complementary', { name: 'Filters' })).toBeVisible()
    await expect(canvas.queryByRole('complementary', { name: 'Game details' })).toBeNull()
  },
}

export const WithPanel: Story = { args: { panel: <p>Super Metroid</p> } }
