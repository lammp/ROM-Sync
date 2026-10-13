import { composeStories } from '@storybook/react'
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import * as stories from './PasswordInput.stories'

const { Stored, NotSet } = composeStories(stories)

describe('PasswordInput', () => {
  it('masks what is typed and is named by its label', () => {
    render(<Stored />)
    const field = screen.getByLabelText('IGDB client secret') as HTMLInputElement
    expect(field.type).toBe('password')
    expect(field.autocomplete).toBe('off')
  })

  it('says a secret is stored without showing it', () => {
    render(<Stored />)
    const field = screen.getByLabelText('IGDB client secret') as HTMLInputElement
    expect(field.value).toBe('')
    expect(field.placeholder).toBe('Stored. Type to replace.')
  })

  it('says when nothing is stored', () => {
    render(<NotSet />)
    expect((screen.getByLabelText('IGDB client secret') as HTMLInputElement).placeholder).toBe(
      'Not set',
    )
  })
})
