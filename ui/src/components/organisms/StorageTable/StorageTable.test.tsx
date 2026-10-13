import { composeStories } from '@storybook/react'
import { render, screen, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { formatBytes } from '../../../lib/format/format'
import * as stories from './StorageTable.stories'

const { Measured, NothingYet } = composeStories(stories)

describe('StorageTable', () => {
  it('names each part, with its files, size, share and what upkeep reclaims', () => {
    render(<Measured />)
    const mb = (n: number) => formatBytes(n * 1024 * 1024)
    const table = screen.getByRole('table', {
      name: `Storage: ${mb(500)}, ${mb(74)} reclaimable`,
    })
    const rows = within(table).getAllByRole('row').slice(1)
    expect(
      rows.map((r) =>
        within(r)
          .getAllByRole('cell')
          .map((c) => c.textContent),
      ),
    ).toEqual([
      ['Database', '2', mb(40), '8%', mb(4)],
      ['Covers', '1,200', mb(300), '60%', mb(20)],
      ['Screenshot and artwork cache', '80', mb(50), '10%', mb(50)],
      ['Logs', '3', mb(2), '0%', ''],
      ['Sync run folders', '120', mb(8), '2%', ''],
      ['Working files', '0', formatBytes(0), '0%', ''],
      ['Embedded browser profile', '400', mb(100), '20%', ''],
    ])
  })

  it('says nothing is measured before the first read', () => {
    render(<NothingYet />)
    expect(screen.getByText('Nothing measured yet.')).toBeTruthy()
  })
})
