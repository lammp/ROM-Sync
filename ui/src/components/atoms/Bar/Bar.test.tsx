import { composeStories } from '@storybook/react'
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { Bar } from './Bar'
import * as stories from './Bar.stories'

const { Partly, Full } = composeStories(stories)

describe('Bar', () => {
  it('is a named meter reporting its percentage', () => {
    render(<Partly />)
    const meter = screen.getByRole('meter', { name: 'Space used' })
    expect(meter.getAttribute('aria-valuenow')).toBe('62')
    expect(meter.getAttribute('aria-valuetext')).toBe('62%')
  })

  it('announces what a value means when told', () => {
    render(<Full />)
    expect(screen.getByRole('meter').getAttribute('aria-valuetext')).toBe('512 GB of 512 GB')
  })

  it('holds a value outside 0 to 1, and a missing one, to the ends', () => {
    for (const [value, now] of [
      [-1, '0'],
      [3, '100'],
      [Number.NaN, '0'],
    ] as const) {
      const { unmount } = render(<Bar value={value} label="x" />)
      expect(screen.getByRole('meter').getAttribute('aria-valuenow')).toBe(now)
      unmount()
    }
  })
})
