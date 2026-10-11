import { composeStories } from '@storybook/react'
import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { parseTag } from './TagAdd'
import * as stories from './TagAdd.stories'

const { Default } = composeStories(stories)

describe('TagAdd', () => {
  it('reads a kind prefix as version 1 did, and anything else as a user tag', () => {
    expect(parseTag('theme : Horror')).toEqual({ kind: 'theme', tag: 'Horror' })
    expect(parseTag('GENRE:RPG')).toEqual({ kind: 'genre', tag: 'RPG' })
    expect(parseTag('mode: co-op')).toEqual({ kind: 'user', tag: 'mode: co-op' })
    expect(parseTag('  ')).toBeNull()
  })

  it('adds on the button and clears the field', () => {
    render(<Default />)
    const box = screen.getByRole('textbox', { name: 'Add a tag' }) as HTMLInputElement
    fireEvent.change(box, { target: { value: 'Favourites' } })
    fireEvent.click(screen.getByRole('button', { name: 'Add' }))
    expect(Default.args.onAdd).toHaveBeenCalledWith({ kind: 'user', tag: 'Favourites' })
    expect(box.value).toBe('')
  })
})
