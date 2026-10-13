import { composeStories } from '@storybook/react'
import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import * as stories from './PromptDialog.stories'

const { Rename } = composeStories(stories)

describe('PromptDialog', () => {
  it('focuses the field with its current value', () => {
    render(<Rename />)
    const field = screen.getByRole('textbox', { name: 'Name' }) as HTMLInputElement
    expect(document.activeElement).toBe(field)
    expect(field.value).toBe('Thor')
  })

  it('submits the trimmed answer and refuses a blank one', () => {
    render(<Rename />)
    const field = screen.getByRole('textbox', { name: 'Name' })
    fireEvent.change(field, { target: { value: '   ' } })
    expect((screen.getByRole('button', { name: 'Rename' }) as HTMLButtonElement).disabled).toBe(
      true,
    )
    fireEvent.change(field, { target: { value: ' Thor Max ' } })
    fireEvent.click(screen.getByRole('button', { name: 'Rename' }))
    expect(Rename.args.onSubmit).toHaveBeenCalledWith('Thor Max')
  })
})
