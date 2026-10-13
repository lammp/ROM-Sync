import { composeStories } from '@storybook/react'
import { fireEvent, render, screen, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import * as stories from './SysfilesOthers.stories'

const { Stray, Removing, NothingStray } = composeStories(stories)

describe('SysfilesOthers', () => {
  it('lists each stray item with its folder and size, and removes one', () => {
    render(<Stray />)
    const rows = within(screen.getByRole('table', { name: 'Stray files' }))
      .getAllByRole('row')
      .slice(1)
    expect(
      rows.map((r) => [...r.querySelectorAll('td')].slice(0, 3).map((c) => c.textContent)),
    ).toEqual([
      ['ROM-Sync/bios/gba', 'old_bios.bin', '16.0 KB'],
      ['ROM-Sync/bios', 'notes (folder)', ''],
    ])
    fireEvent.click(screen.getByRole('button', { name: 'Remove notes' }))
    expect(Stray.args.onRemove).toHaveBeenCalledWith(Stray.args.others?.[1])
  })

  it('holds every Remove while one runs, and says which', () => {
    render(<Removing />)
    expect(screen.getByRole('button', { name: 'Removing old_bios.bin' }).textContent).toBe(
      'Removing…',
    )
    expect(screen.getAllByRole('button').every((b) => b.hasAttribute('disabled'))).toBe(true)
  })

  it('says when nothing is stray', () => {
    render(<NothingStray />)
    expect(screen.getByText('nothing stray')).toBeTruthy()
  })
})
