import { composeStories } from '@storybook/react'
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import * as stories from './CapacityMeter.stories'

const { Green, Yellow, Red, Full, Unknown, Live } = composeStories(stories)

describe('CapacityMeter', () => {
  it('five_states: each draws its level in words as well as colour', () => {
    const states: [typeof Green, string][] = [
      [Green, 'fits'],
      [Yellow, 'getting full'],
      [Red, 'nearly full'],
      [Full, 'will not fit'],
      [Unknown, 'capacity unknown'],
    ]
    for (const [Story, word] of states) {
      const { unmount } = render(<Story />)
      expect(screen.getByText(new RegExp(word))).toBeTruthy()
      const meter = screen.queryByRole('meter') ?? screen.getByRole('img')
      expect(meter.getAttribute('aria-valuetext') ?? meter.getAttribute('aria-label')).toContain(
        word,
      )
      unmount()
    }
  })

  it('thresholds_from_settings: the level arrives in the reading, computed from settings', () => {
    render(<Yellow />)
    expect(Yellow.args.reading?.level).toBe('yellow')
    expect(screen.getByText('getting full')).toBeTruthy()
  })

  it('says how much a sync that will not fit is short by', () => {
    render(<Full />)
    expect(screen.getByText(/short by 4\.50 GB/)).toBeTruthy()
  })

  it('shows free space now and after while a sync runs', () => {
    render(<Live />)
    expect(screen.getByText(/40\.0 GB free now → 34\.0 GB after/)).toBeTruthy()
  })

  it('reports the percentage after the sync', () => {
    render(<Red />)
    expect(screen.getByRole('meter').getAttribute('aria-valuenow')).toBe('91')
  })
})
