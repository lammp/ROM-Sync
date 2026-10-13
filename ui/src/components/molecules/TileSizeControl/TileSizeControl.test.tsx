import { composeStories } from '@storybook/react'
import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { TILE_MAX, TILE_MIN } from '../../../design/tokens/tokens'
import * as stories from './TileSizeControl.stories'

const { Default } = composeStories(stories)

describe('TileSizeControl', () => {
  it('runs over version 1s range, 90 to 260 px, from the one definition', () => {
    render(<Default />)
    const slider = screen.getByRole('slider') as HTMLInputElement
    expect([slider.min, slider.max]).toEqual([String(TILE_MIN), String(TILE_MAX)])
    expect([TILE_MIN, TILE_MAX]).toEqual([90, 260])
  })

  it('reports the width chosen', () => {
    render(<Default />)
    fireEvent.change(screen.getByRole('slider'), { target: { value: '200' } })
    expect(Default.args.onChange).toHaveBeenCalledWith(200)
  })
})
