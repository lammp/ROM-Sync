import { composeStories } from '@storybook/react'
import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import * as stories from './Button.stories'

const { Default, Primary, Danger, Active, Small, Disabled } = composeStories(stories)

describe('Button', () => {
  it('is a button that never submits by accident', () => {
    render(<Default />)
    expect(screen.getByRole('button').getAttribute('type')).toBe('button')
  })

  it('calls back on a click', () => {
    render(<Default />)
    fireEvent.click(screen.getByRole('button'))
    expect(Default.args.onClick).toHaveBeenCalled()
  })

  it('renders every variant as a labelled button', () => {
    for (const [Story, name] of [
      [Primary, 'Sync now'],
      [Danger, 'Remove profile'],
      [Small, 'Accept'],
    ] as const) {
      const { unmount } = render(<Story />)
      expect(screen.getByRole('button', { name })).toBeTruthy()
      unmount()
    }
  })

  it('announces a toggle as pressed, and only a toggle', () => {
    render(<Active />)
    expect(screen.getByRole('button').getAttribute('aria-pressed')).toBe('true')
  })

  it('leaves aria-pressed off a plain button', () => {
    render(<Default />)
    expect(screen.getByRole('button').hasAttribute('aria-pressed')).toBe(false)
  })

  it('ignores a click while disabled', () => {
    render(<Disabled />)
    fireEvent.click(screen.getByRole('button'))
    expect(Disabled.args.onClick).not.toHaveBeenCalled()
  })
})
