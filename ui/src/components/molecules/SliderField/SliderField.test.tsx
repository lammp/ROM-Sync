import { composeStories } from '@storybook/react'
import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import * as stories from './SliderField.stories'

const { Threshold, Count, Linked, Refused } = composeStories(stories)

describe('SliderField', () => {
  it('pairs a scale with its number, each named', () => {
    render(<Threshold />)
    const scale = screen.getByRole('slider', { name: 'Match acceptance threshold, scale' })
    expect(scale.getAttribute('min')).toBe('0')
    expect(scale.getAttribute('max')).toBe('1')
    expect(scale.getAttribute('aria-valuetext')).toBe('0.55')
    fireEvent.change(scale, { target: { value: '0.6' } })
    expect(Threshold.args.onChange).toHaveBeenCalledWith('0.60')
  })

  it('writes whole steps as whole numbers', () => {
    render(<Count />)
    fireEvent.change(screen.getByRole('slider'), { target: { value: '40' } })
    expect(Count.args.onChange).toHaveBeenCalledWith('40')
  })

  it('moves the scale as the number is typed', () => {
    render(<Linked />)
    fireEvent.change(screen.getByRole('textbox'), { target: { value: '0.8' } })
    expect((screen.getByRole('slider') as HTMLInputElement).value).toBe('0.8')
  })

  it('rests the scale at its end for a number past it, and says why', () => {
    render(<Refused />)
    expect((screen.getByRole('slider') as HTMLInputElement).value).toBe('1')
    expect(screen.getByRole('textbox').getAttribute('aria-invalid')).toBe('true')
    expect(screen.getByText('At most 1')).toBeTruthy()
  })
})
