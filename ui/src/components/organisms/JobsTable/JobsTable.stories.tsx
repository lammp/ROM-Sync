import type { Meta, StoryObj } from '@storybook/nextjs-vite'
import { expect, fn } from 'storybook/test'
import { JobsTable } from './JobsTable'

const meta = {
  title: 'Organisms/JobsTable',
  component: JobsTable,
  args: {
    jobs: [
      {
        id: 'j3',
        kind: 'match',
        started: '2026-10-11T12:04:00',
        state: 'running',
        progress: { phase: 'match', done: 120, total: 800 },
        error: null,
      },
      {
        id: 'j2',
        kind: 'scan',
        started: '2026-10-11T12:00:00',
        state: 'done',
        progress: null,
        error: null,
      },
      {
        id: 'j1',
        kind: 'sync',
        started: '2026-10-10T20:00:00',
        state: 'failed',
        progress: null,
        error: 'Thor went away',
      },
    ],
    onCancel: fn(),
  },
} satisfies Meta<typeof JobsTable>

export default meta
type Story = StoryObj<typeof meta>

export const Default: Story = {
  play: async ({ canvas, args, userEvent }) => {
    await userEvent.click(canvas.getByRole('button', { name: 'Cancel match' }))
    await expect(args.onCancel).toHaveBeenCalledWith('j3')
  },
}

export const None: Story = { args: { jobs: [] } }
