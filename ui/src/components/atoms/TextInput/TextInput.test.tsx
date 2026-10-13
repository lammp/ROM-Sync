import { composeStories } from '@storybook/react'
import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import * as stories from './TextInput.stories'

const { Default, Invalid, HiddenLabel, WithHelp } = composeStories(stories)

describe('TextInput', () => {
  it('is named by its label', () => {
    render(<Default />)
    expect((screen.getByLabelText('Store folder') as HTMLInputElement).value).toBe(
      'D:\\Games\\ROMs',
    )
  })

  it('reports each change as the new value', () => {
    render(<Default />)
    fireEvent.change(screen.getByRole('textbox'), { target: { value: 'E:\\ROMs' } })
    expect(Default.args.onChange).toHaveBeenCalledWith('E:\\ROMs')
  })

  it('ties an error to the field and marks it invalid', () => {
    render(<Invalid />)
    const input = screen.getByRole('textbox')
    expect(input.getAttribute('aria-invalid')).toBe('true')
    const described = document.getElementById(input.getAttribute('aria-describedby') ?? '')
    expect(described?.textContent).toBe('That folder does not exist.')
  })

  it('keeps a hidden label announced', () => {
    render(<HiddenLabel />)
    expect(screen.getByLabelText('New tag')).toBeTruthy()
  })

  it('ties a help line to the field, beside any error', () => {
    render(<WithHelp />)
    const ids = screen.getByRole('textbox').getAttribute('aria-describedby')?.split(' ') ?? []
    expect(ids.map((id) => document.getElementById(id)?.textContent)).toEqual([
      'The library every device is synced from.',
      'That folder does not exist.',
    ])
  })
})
