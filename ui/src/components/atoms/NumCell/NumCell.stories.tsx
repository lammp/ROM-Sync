import type { Meta, StoryObj } from '@storybook/nextjs-vite'
import { expect } from 'storybook/test'
import { NumCell } from './NumCell'

const meta = {
  title: 'Atoms/NumCell',
  component: NumCell,
  args: { children: '1,284' },
  decorators: [
    (Story) => (
      <table>
        <tbody>
          <tr>
            <td>Games</td>
            {Story()}
          </tr>
        </tbody>
      </table>
    ),
  ],
} satisfies Meta<typeof NumCell>

export default meta
type Story = StoryObj<typeof meta>

export const Cell: Story = {
  play: async ({ canvas }) => {
    await expect(canvas.getByRole('cell', { name: '1,284' })).toBeVisible()
  },
}

export const Header: Story = {
  args: { header: true, children: 'Size' },
  decorators: [
    (Story) => (
      <table>
        <thead>
          <tr>
            <th scope="col">System</th>
            {Story()}
          </tr>
        </thead>
      </table>
    ),
  ],
}
