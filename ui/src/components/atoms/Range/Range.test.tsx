import { composeStories } from '@storybook/react'
import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import * as stories from './Range.stories'

const { TileSize, RatingFloor } = composeStories(stories)

describe('Range', () => {
  it('is a labelled slider over its range', () => {
    render(<TileSize />)
    const slider = screen.getByRole('slider', { name: 'Tiles' }) as HTMLInputElement
    expect([slider.min, slider.max, slider.value]).toEqual(['90', '260', '150'])
  })

  it('reports the new value as a number', () => {
    render(<TileSize />)
    fireEvent.change(screen.getByRole('slider'), { target: { value: '200' } })
    expect(TileSize.args.onChange).toHaveBeenCalledWith(200)
  })

  it('announces what the value means', () => {
    render(<RatingFloor />)
    expect(screen.getByRole('slider').getAttribute('aria-valuetext')).toBe('any')
  })
})
