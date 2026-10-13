import { composeStories } from '@storybook/react'
import { render, screen, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import * as stories from './MaintenanceTable.stories'

const { Default, Busy } = composeStories(stories)

describe('MaintenanceTable', () => {
  it('says what each action would remove, and runs only one with something to remove', () => {
    render(<Default />)
    const rows = within(screen.getByRole('table', { name: 'Upkeep' }))
      .getAllByRole('row')
      .slice(1)
    expect(rows.map((r) => r.querySelectorAll('td')[1]?.textContent)).toEqual([
      '12 · 3.24 MB',
      '0 · 0 B',
      'checking…',
    ])
    expect(
      screen.getByRole('button', { name: 'Delete unreferenced covers' }).hasAttribute('disabled'),
    ).toBe(false)
    expect(
      screen.getByRole('button', { name: 'Clear the screenshot cache' }).hasAttribute('disabled'),
    ).toBe(true)
    expect(
      screen.getByRole('button', { name: 'Compact the database' }).hasAttribute('disabled'),
    ).toBe(true)
  })

  it('holds every action while one runs', () => {
    render(<Busy />)
    expect(screen.getAllByRole('button').every((b) => b.hasAttribute('disabled'))).toBe(true)
  })
})
