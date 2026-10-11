import { composeStories } from '@storybook/react'
import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import * as stories from './GridListToggle.stories'

const { Grid, List } = composeStories(stories)

describe('GridListToggle', () => {
  it('shows which view is on', () => {
    render(<List />)
    expect(screen.getByRole('button', { name: 'List' }).getAttribute('aria-pressed')).toBe('true')
    expect(screen.getByRole('button', { name: 'Grid' }).getAttribute('aria-pressed')).toBe('false')
    expect(screen.getByRole('group', { name: 'View' })).toBeTruthy()
  })

  it('reports only a change', () => {
    render(<Grid />)
    fireEvent.click(screen.getByRole('button', { name: 'Grid' }))
    expect(Grid.args.onChange).not.toHaveBeenCalled()
  })
})
