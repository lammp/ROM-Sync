import { composeStories } from '@storybook/react'
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import * as stories from './VersionPicker.stories'

const { Two, One } = composeStories(stories)

describe('VersionPicker', () => {
  it('orders versions by system and says which is selected and which is loose', () => {
    render(<Two />)
    expect(screen.getAllByRole('option').map((o) => o.textContent)).toEqual([
      'Nintendo 3DS · 2015 (loose)',
      'Nintendo 64 · 2000 ✓ selected',
    ])
  })

  it('is just the system with one version', () => {
    render(<One />)
    expect(screen.queryByRole('combobox')).toBeNull()
    expect(screen.getByText('Nintendo 64')).toBeTruthy()
  })
})
