import { composeStories } from '@storybook/react'
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import * as stories from './Dot.stories'

const { Neutral, Ok, Bad } = composeStories(stories)

describe('Dot', () => {
  it('is named by its label', () => {
    render(<Ok />)
    expect(screen.getByRole('img', { name: 'Ready' })).toBeTruthy()
  })

  it('is hidden when it only repeats the text beside it', () => {
    const { container } = render(<Neutral />)
    expect(screen.queryByRole('img')).toBeNull()
    expect(container.querySelector('span')?.getAttribute('aria-hidden')).toBe('true')
  })

  it('names a failure', () => {
    render(<Bad />)
    expect(screen.getByRole('img', { name: 'Missing files' })).toBeTruthy()
  })
})
