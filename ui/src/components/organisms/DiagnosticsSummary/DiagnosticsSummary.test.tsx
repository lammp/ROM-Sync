import { composeStories } from '@storybook/react'
import { render, screen, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import * as stories from './DiagnosticsSummary.stories'

const { Working, FirstRun } = composeStories(stories)

const facts = () => {
  const list = screen.getByLabelText('Diagnostics')
  const terms = within(list)
    .getAllByRole('term')
    .map((t) => t.textContent)
  const values = within(list)
    .getAllByRole('definition')
    .map((d) => d.textContent)
  return Object.fromEntries(terms.map((t, i) => [t, values[i]]))
}

describe('DiagnosticsSummary', () => {
  it('says each fact, the last sync in words, and each recent failure', () => {
    render(<Working />)
    expect(facts()).toEqual({
      Version: 'ROM-Sync 2.0.0 · API v1',
      Shell: 'desktop window',
      Address: 'http://127.0.0.1:8765/',
      'Data folder': 'X:/LocalAppData/ROM-Sync/data',
      'Log folder': 'X:/LocalAppData/ROM-Sync/data/logs',
      'Last sync': 'Thor · 2026-10-04 09:00 · done · sent 12 · removed 3 · 3.00 GB',
    })
    const failed = within(screen.getByRole('list', { name: 'Recent errors' })).getByRole('listitem')
    expect(failed.textContent).toBe(
      'scan · 2026-10-05 08:15 · store.unreadablethe store folder could not be read',
    )
  })

  it('offers the support bundle as a download', () => {
    render(<Working />)
    const link = screen.getByRole('link', { name: 'Export a support bundle' })
    expect(link.getAttribute('href')).toBe('/api/v1/diagnostics/bundle')
    expect(link.getAttribute('download')).toBe('romsync-support.zip')
  })

  it('says plainly when nothing has synced or failed yet', () => {
    render(<FirstRun />)
    expect(facts()['Last sync']).toBe('no sync yet')
    expect(screen.getByText('No job has failed.')).toBeTruthy()
    expect(screen.queryByRole('list', { name: 'Recent errors' })).toBeNull()
  })
})
