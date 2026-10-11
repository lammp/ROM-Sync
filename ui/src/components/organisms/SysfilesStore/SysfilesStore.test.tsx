import { composeStories } from '@storybook/react'
import { render, screen, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import * as stories from './SysfilesStore.stories'

const { Default, Empty } = composeStories(stories)

describe('SysfilesStore', () => {
  it('lists every file with the store’s copy in words', () => {
    render(<Default />)
    const rows = within(screen.getByRole('table', { name: 'System files in the store' }))
      .getAllByRole('row')
      .slice(1)
    expect(rows.map((r) => r.querySelectorAll('td')[4]?.textContent)).toEqual([
      '16.0 KB verified',
      '4.00 MB not a known dump',
      'missing',
    ])
  })

  it('says when the registry lists nothing', () => {
    render(<Empty />)
    expect(screen.getByText('The registry lists no system files.')).toBeTruthy()
  })
})
