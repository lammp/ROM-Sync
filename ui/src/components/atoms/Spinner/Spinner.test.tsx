import { composeStories } from '@storybook/react'
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import * as stories from './Spinner.stories'

const { Working, Syncing } = composeStories(stories)

describe('Spinner', () => {
  it('is named for the work it shows', () => {
    render(<Working />)
    expect(screen.getByRole('img', { name: 'Working' })).toBeTruthy()
  })

  it('takes a specific name', () => {
    render(<Syncing />)
    expect(screen.getByRole('img', { name: 'Syncing' })).toBeTruthy()
  })
})
