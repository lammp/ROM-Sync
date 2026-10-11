import { composeStories } from '@storybook/react'
import { render, screen, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { progressText } from './JobsTable'
import * as stories from './JobsTable.stories'

const { Default, None } = composeStories(stories)

describe('JobsTable', () => {
  it('lists each job with its state in words, its progress or its error, and Cancel only while it runs', () => {
    render(<Default />)
    const rows = within(screen.getByRole('table', { name: 'Jobs' }))
      .getAllByRole('row')
      .slice(1)
    expect(rows.map((r) => [...r.querySelectorAll('td')].map((c) => c.textContent))).toEqual([
      ['match', '2026-10-11 12:04', 'running', 'match 120 of 800', 'Cancel'],
      ['scan', '2026-10-11 12:00', 'done', '', ''],
      ['sync', '2026-10-10 20:00', 'failed', 'Thor went away', ''],
    ])
  })

  it('says when there are no jobs', () => {
    render(<None />)
    expect(screen.getByText('No jobs yet.')).toBeTruthy()
  })

  it('words progress with or without a total', () => {
    expect([progressText(null), progressText({ phase: 'scan', done: 3, total: null })]).toEqual([
      '',
      'scan',
    ])
  })
})
