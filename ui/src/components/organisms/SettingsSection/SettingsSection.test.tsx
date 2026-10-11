import { composeStories } from '@storybook/react'
import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import * as stories from './SettingsSection.stories'

const { Clean, Edited, Saving, Problem, NothingToSave } = composeStories(stories)

describe('SettingsSection', () => {
  it('is a region named by its title, saving only once something is edited', () => {
    render(<Clean />)
    expect(screen.getByRole('region', { name: /^Library/ }).id).toBe('library')
    expect(screen.getByRole('button', { name: 'Save library' }).hasAttribute('disabled')).toBe(true)
    expect(screen.getByText('4 systems')).toBeTruthy()
  })

  it('says it is edited and saves', () => {
    render(<Edited />)
    expect(screen.getByText('edited')).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: 'Save library' }))
    expect(Edited.args.onSave).toHaveBeenCalledTimes(1)
  })

  it('cannot be saved twice at once', () => {
    render(<Saving />)
    expect(screen.getByRole('button', { name: 'Saving…' }).hasAttribute('disabled')).toBe(true)
  })

  it('says a problem in words', () => {
    render(<Problem />)
    expect(screen.getByText('no store chosen')).toBeTruthy()
  })

  it('has no Save when there is nothing to save', () => {
    render(<NothingToSave />)
    expect(screen.queryByRole('button')).toBeNull()
  })
})
