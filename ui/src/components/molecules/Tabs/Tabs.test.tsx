import { composeStories } from '@storybook/react'
import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import * as stories from './Tabs.stories'

const { Switching } = composeStories(stories)

describe('Tabs', () => {
  it('shows one panel and keeps the others mounted, hidden', () => {
    render(<Switching />)
    expect(screen.getByRole('tab', { name: 'Library' }).getAttribute('aria-selected')).toBe('true')
    const kept = screen.getByLabelText('Client ID')
    fireEvent.change(kept, { target: { value: 'typed' } })
    fireEvent.click(screen.getByRole('tab', { name: 'Diagnostics' }))
    fireEvent.click(screen.getByRole('tab', { name: /^Metadata/ }))
    expect((screen.getByLabelText('Client ID') as HTMLInputElement).value).toBe('typed')
  })

  it('moves with the arrow keys, Home and End', () => {
    render(<Switching />)
    const first = screen.getByRole('tab', { name: 'Library' })
    fireEvent.keyDown(first, { key: 'End' })
    expect(Switching.args.onSelect).toHaveBeenLastCalledWith('diagnostics')
    fireEvent.keyDown(first, { key: 'ArrowRight' })
    expect(Switching.args.onSelect).toHaveBeenLastCalledWith('library')
  })

  it('names an edited tab as edited', () => {
    render(<Switching />)
    expect(screen.getByRole('tab', { name: 'Metadata and artwork, unsaved changes' })).toBeTruthy()
  })
})
