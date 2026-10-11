import { composeStories } from '@storybook/react'
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import * as stories from './NumCell.stories'

const { Cell, Header } = composeStories(stories)

describe('NumCell', () => {
  it('is a data cell', () => {
    render(<Cell />)
    expect(screen.getByRole('cell', { name: '1,284' }).tagName).toBe('TD')
  })

  it('is a column header when asked', () => {
    render(<Header />)
    expect(screen.getByRole('columnheader', { name: 'Size' }).getAttribute('scope')).toBe('col')
  })
})
