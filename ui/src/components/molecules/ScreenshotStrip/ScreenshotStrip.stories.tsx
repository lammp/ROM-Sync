import type { Meta, StoryObj } from '@storybook/nextjs-vite'
import { expect, fn } from 'storybook/test'
import { ScreenshotStrip } from './ScreenshotStrip'

const shot = (n: number) =>
  'data:image/svg+xml;utf8,' +
  encodeURIComponent(
    `<svg xmlns="http://www.w3.org/2000/svg" width="${160 + n}" height="96"><rect width="100%" height="100%"/></svg>`,
  )

const meta = {
  title: 'Molecules/ScreenshotStrip',
  component: ScreenshotStrip,
  args: {
    title: 'Super Metroid',
    onOpen: fn(),
    shots: [1, 2, 3].map((n) => ({ thumb: shot(n), full: shot(n * 10) })),
  },
  decorators: [
    (Story) => <div style={{ background: 'var(--bg2)', padding: 12, width: 388 }}>{Story()}</div>,
  ],
} satisfies Meta<typeof ScreenshotStrip>

export default meta
type Story = StoryObj<typeof meta>

export const Three: Story = {
  play: async ({ canvas, args, userEvent }) => {
    await userEvent.click(canvas.getByRole('img', { name: 'Super Metroid, screenshot 2' }))
    await expect(args.onOpen).toHaveBeenCalledWith(args.shots[1])
  },
}

export const None: Story = { args: { shots: [] } }
