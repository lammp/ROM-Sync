import type { Meta, StoryObj } from '@storybook/nextjs-vite'
import { expect } from 'storybook/test'
import { SysfileReqRow, type Requirement } from './SysfileReqRow'

const req: Requirement = {
  name: 'scph5501.bin',
  stagedName: 'scph5501.bin',
  note: 'North American BIOS',
  required: true,
  group: false,
  store: { present: true, size: 524288, verified: true },
  staged: 'current',
  installed: 'installed',
  installedPath: '/storage/emulated/0/RetroArch/system/scph5501.bin',
}

const meta = {
  title: 'Molecules/SysfileReqRow',
  component: SysfileReqRow,
  args: { req },
  decorators: [
    (Story) => (
      <table style={{ background: 'var(--bg2)' }}>
        <thead>
          <tr>
            {['Item', 'Need', 'Store', 'Staged', 'Installed'].map((h) => (
              <th key={h} scope="col">
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>{Story()}</tbody>
      </table>
    ),
  ],
} satisfies Meta<typeof SysfileReqRow>

export default meta
type Story = StoryObj<typeof meta>

export const AllGood: Story = {
  play: async ({ canvas }) => {
    await expect(canvas.getByText('512.0 KB verified')).toBeVisible()
    await expect(canvas.getByText('installed')).toBeVisible()
  },
}

export const Missing: Story = {
  args: {
    req: {
      ...req,
      store: { present: false, size: null, verified: null },
      staged: 'absent',
      installed: 'missing',
    },
  },
}

export const Different: Story = {
  args: {
    req: {
      ...req,
      stagedName: 'bios.bin',
      group: true,
      required: false,
      store: { present: true, size: 524288, verified: false },
      staged: 'different',
      installed: 'unseen',
    },
  },
}
