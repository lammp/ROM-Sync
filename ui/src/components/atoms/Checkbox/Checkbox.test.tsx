import { composeStories } from '@storybook/react'
import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import * as stories from './Checkbox.stories'

const { Unchecked, Checked } = composeStories(stories)

describe('Checkbox', () => {
  it('is named by its label', () => {
    render(<Checked />)
    expect(
      (screen.getByRole('checkbox', { name: 'Only on the device' }) as HTMLInputElement).checked,
    ).toBe(true)
  })

  it('toggles from a click on the label', () => {
    render(<Unchecked />)
    fireEvent.click(screen.getByText('Only on the device'))
    expect(Unchecked.args.onChange).toHaveBeenCalledWith(true)
  })
})
