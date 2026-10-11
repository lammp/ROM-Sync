import { composeStories } from '@storybook/react'
import { fireEvent, render, screen, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import * as stories from './SyncConfirm.stories'

const { Default, SendOnly, Starting } = composeStories(stories)

const cells = () =>
  within(screen.getByRole('table', { name: 'What the sync will do' }))
    .getAllByRole('row')
    .slice(1)
    .map((r) => [...r.querySelectorAll('td')].map((c) => c.textContent))

describe('SyncConfirm', () => {
  it('lists what the sync will send, replace and remove, and the space after', () => {
    render(<Default />)
    expect(cells()).toEqual([
      ['Send', '2', '7.00 MB'],
      ['Replace', '1', '2.00 MB'],
      ['Remove from device', '1', '1.00 MB'],
      ['Already in place', '120', ''],
    ])
    expect(
      screen.getByText(/Net change 8\.00 MB · 1\.00 GB free now, 1016\.0 MB after/),
    ).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: 'Cancel' }))
    expect(Default.args.onCancel).toHaveBeenCalled()
    expect(Default.args.onStart).not.toHaveBeenCalled()
  })

  it('leaves out what the sync will not do, and the space when it is unknown', () => {
    render(<SendOnly />)
    expect(cells().map((r) => r[0])).toEqual(['Send', 'Already in place'])
    expect(screen.queryByText(/free now/)).toBeNull()
  })

  it('cannot be started twice', () => {
    render(<Starting />)
    expect(screen.getByRole('button', { name: 'Starting…' }).hasAttribute('disabled')).toBe(true)
  })
})
