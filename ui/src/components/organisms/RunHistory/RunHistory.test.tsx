import { composeStories } from '@storybook/react'
import { render, screen, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import * as stories from './RunHistory.stories'

const { Default, NoRuns } = composeStories(stories)

describe('RunHistory', () => {
  it('lists each run with its state in words, its counts and what it moved', () => {
    render(<Default />)
    const rows = within(screen.getByRole('table', { name: 'History' }))
      .getAllByRole('row')
      .slice(1)
    expect(rows.map((r) => [...r.querySelectorAll('td')].map((c) => c.textContent))).toEqual([
      ['#12', '2026-10-10 21:04', 'failed', '38', '', '2', '2', '3.03 GB'],
      ['#11', '2026-10-08 19:30', 'done', '3', '1', '1', '', '420.0 MB'],
      ['#10', '2026-10-07 08:00', 'cancelled', '1', '', '', '', '12.0 MB'],
    ])
  })

  it('says when there are no runs yet', () => {
    render(<NoRuns />)
    expect(screen.getByText('no runs yet')).toBeTruthy()
  })
})
