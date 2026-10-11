import { composeStories } from '@storybook/react'
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import * as stories from './DataTable.stories'

const { Two, Empty } = composeStories(stories)

describe('DataTable', () => {
  it('is a captioned table with column headers', () => {
    render(<Two />)
    expect(screen.getByRole('table', { name: 'Systems on Thor' })).toBeTruthy()
    expect(screen.getAllByRole('columnheader').map((h) => h.textContent)).toEqual([
      'System',
      'Games',
      'Size',
    ])
    expect(screen.getAllByRole('row')).toHaveLength(3)
  })

  it('says so when there are no rows', () => {
    render(<Empty />)
    expect(screen.getByRole('cell', { name: 'Nothing on the device yet.' })).toBeTruthy()
  })
})
