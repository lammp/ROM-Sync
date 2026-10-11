import { composeStories } from '@storybook/react'
import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import * as stories from './PlanLine.stories'

const { Changes, InStep, DoesNotFit } = composeStories(stories)

describe('PlanLine', () => {
  it('says what the sync will do and names folders it leaves alone', () => {
    render(<Changes />)
    expect(screen.getByText(/Sync will/).textContent).toContain(
      'send 2 (11.0 MB), remove 1 (128.0 KB)',
    )
    expect(screen.getByText(/left alone/).textContent).toContain('pico8 (12)')
    expect(screen.getByText('fits')).toBeTruthy()
  })

  it('shows and hides the list', () => {
    render(<Changes />)
    expect(screen.queryByText('the full list')).toBeNull()
    fireEvent.click(screen.getByRole('button', { name: 'show list' }))
    expect(screen.getByText('the full list')).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: 'hide list' }))
    expect(screen.queryByText('the full list')).toBeNull()
  })

  it('says when nothing needs doing', () => {
    render(<InStep />)
    expect(screen.getByText('the device matches your selection')).toBeTruthy()
  })

  it('says when it does not fit', () => {
    render(<DoesNotFit />)
    expect(screen.getByText('does not fit')).toBeTruthy()
  })
})
