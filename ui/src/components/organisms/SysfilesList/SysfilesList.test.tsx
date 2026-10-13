import { composeStories } from '@storybook/react'
import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import * as stories from './SysfilesList.stories'

const { Default, NothingStray } = composeStories(stories)

describe('SysfilesList', () => {
  it('puts the systems on the device first, most games first, then the rest, then stray files', () => {
    render(<Default />)
    const items = screen.getAllByRole('listitem').map((li) => li.textContent)
    expect(items).toEqual([
      expect.stringMatching(/^Super Nintendo/),
      expect.stringMatching(/^Game Boy Advance/),
      expect.stringMatching(/^PlayStation 2/),
      'in the store, not on the device',
      expect.stringMatching(/^Nintendo 64/),
      'ROM-Sync/bios',
      'Other files2 stray',
    ])
  })

  it('marks the system in view and selects another', () => {
    render(<Default />)
    expect(
      screen.getByRole('button', { name: /^Game Boy Advance/ }).getAttribute('aria-current'),
    ).toBe('true')
    fireEvent.click(screen.getByRole('button', { name: /^PlayStation 2/ }))
    expect(Default.args.onSelect).toHaveBeenCalledWith('ps2')
  })

  it('says when nothing is stray', () => {
    render(<NothingStray />)
    expect(screen.getByRole('button', { name: /^Other files/ }).textContent).toContain('none')
  })
})
