import { composeStories } from '@storybook/react'
import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import * as stories from './ReloadButton.stories'

const { Ready, Busy } = composeStories(stories)

describe('ReloadButton', () => {
  it('is an icon named by what it reads again', () => {
    render(<Ready />)
    const button = screen.getByRole('button', { name: 'Look for devices again' })
    expect(button.querySelector('svg')).not.toBeNull()
    fireEvent.click(button)
    expect(Ready.args.onClick).toHaveBeenCalledOnce()
  })

  it('waits while it reads', () => {
    render(<Busy />)
    const button = screen.getByRole('button', { name: 'Look for devices again' })
    expect((button as HTMLButtonElement).disabled).toBe(true)
    expect(button.getAttribute('aria-busy')).toBe('true')
  })
})
