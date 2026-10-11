import { composeStories } from '@storybook/react'
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import * as stories from './Field.stories'

const { WithHelp, Bare } = composeStories(stories)

describe('Field', () => {
  it('ties the label and the help to the control', () => {
    render(<WithHelp />)
    const input = screen.getByLabelText('Port')
    expect(
      document.getElementById(input.getAttribute('aria-describedby') ?? '')?.textContent,
    ).toContain('this computer only')
  })

  it('describes nothing without help', () => {
    render(<Bare />)
    expect(screen.getByLabelText('Port').hasAttribute('aria-describedby')).toBe(false)
  })
})
