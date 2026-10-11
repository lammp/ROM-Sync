import { composeStories } from '@storybook/react'
import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import * as stories from './DetailPanel.stories'

const { Matched, Unmatched, Folder } = composeStories(stories)

describe('DetailPanel', () => {
  it('shows the game in full', () => {
    render(<Matched />)
    expect(screen.getByRole('article', { name: 'Super Metroid' })).toBeTruthy()
    for (const text of ['1994', '★ 93', '412 votes', '3.00 MB', 'Japan, USA'])
      expect(screen.getByText(text)).toBeTruthy()
    expect(screen.getByText('Samus returns to Zebes to recover the last Metroid.')).toBeTruthy()
  })

  it('says when there is no match yet, and carries the rematch line', () => {
    render(<Unmatched />)
    expect(screen.getByText('No IGDB match yet. The file name is all we know.')).toBeTruthy()
    expect(screen.getByRole('status').textContent).toContain('matching')
    expect(screen.queryByRole('button', { name: /Select for/ })).toBeNull()
  })

  it('counts the files of a folder game', () => {
    render(<Folder />)
    expect(screen.getByText('3.00 MB · 2 files')).toBeTruthy()
  })

  it('closes, takes tags, and refuses an empty rematch', () => {
    render(<Matched />)
    fireEvent.click(screen.getByRole('button', { name: 'Close details' }))
    expect(Matched.args.onClose).toHaveBeenCalled()
    expect((screen.getByRole('button', { name: 'Fix match' }) as HTMLButtonElement).disabled).toBe(
      true,
    )
    fireEvent.click(screen.getByRole('button', { name: 'Accept Metroidvania' }))
    expect(Matched.args.onDecideTag).toHaveBeenCalledWith(Matched.args.tags?.[1], true)
  })
})
