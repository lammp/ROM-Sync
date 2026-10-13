import { composeStories } from '@storybook/react'
import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { stageAction } from './SysfilesDetail'
import * as stories from './SysfilesDetail.stories'

const { Missing, Outdated, Working, NothingNeeded } = composeStories(stories)

describe('SysfilesDetail', () => {
  it('shows a system missing a file, with Add and nothing to remove', () => {
    render(<Missing />)
    const detail = screen.getByRole('article', { name: /^Game Boy Advance/ })
    expect(detail.textContent).toContain('Missing: gba_bios.bin')
    expect(detail.textContent).toContain('120 · 900.0 MB')
    expect(detail.textContent).toContain('not staged in ROM-Sync/bios/gba')
    expect(screen.getByRole('table', { name: 'Files Game Boy Advance needs' })).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: 'Add' }))
    expect(Missing.args.onStage).toHaveBeenCalledTimes(1)
    expect(screen.getByRole('button', { name: 'Remove' }).hasAttribute('disabled')).toBe(true)
  })

  it('offers Update for outdated files and Remove for staged ones', () => {
    render(<Outdated />)
    fireEvent.click(screen.getByRole('button', { name: 'Remove' }))
    expect(Outdated.args.onUnstage).toHaveBeenCalledTimes(1)
    expect(screen.getByRole('button', { name: 'Update' })).toBeTruthy()
  })

  it('holds both actions while one runs', () => {
    render(<Working />)
    expect(screen.getAllByRole('button').every((b) => b.hasAttribute('disabled'))).toBe(true)
  })

  it('says a system needs nothing, and when its emulator has not been seen', () => {
    render(<NothingNeeded />)
    expect(screen.queryByRole('button')).toBeNull()
    expect(screen.getByText('not seen over USB')).toBeTruthy()
    expect(screen.getAllByText('nothing needed').length).toBeGreaterThan(0)
  })

  it('stages only what is absent or outdated', () => {
    expect(
      ['unknown', 'nothing_to_stage', 'absent', 'outdated', 'current'].map((s) =>
        stageAction(s as never),
      ),
    ).toEqual([null, null, 'Add', 'Update', null])
  })
})
