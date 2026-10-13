import { composeStories } from '@storybook/react'
import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { movePair } from './RangeFacet'
import * as stories from './RangeFacet.stories'

const { Year, Size, TypedBound } = composeStories(stories)

describe('RangeFacet', () => {
  describe('paired_thumbs', () => {
    it('never lets the year thumbs cross', () => {
      expect(movePair({ lo: 1975, hi: 1990 }, 'lo', 2000, 0)).toEqual({ lo: 1990, hi: 1990 })
      expect(movePair({ lo: 1995, hi: 2026 }, 'hi', 1980, 0)).toEqual({ lo: 1995, hi: 1995 })
    })

    it('keeps the size thumbs ten steps apart', () => {
      expect(movePair({ lo: 0, hi: 500 }, 'lo', 499, 10)).toEqual({ lo: 490, hi: 500 })
      expect(movePair({ lo: 300, hi: 1000 }, 'hi', 0, 10)).toEqual({ lo: 300, hi: 310 })
    })

    it('moves freely inside the bounds', () => {
      expect(movePair({ lo: 0, hi: 1000 }, 'lo', 250, 10)).toEqual({ lo: 250, hi: 1000 })
    })

    it('holds them in the rendered sliders', () => {
      render(<Size />)
      fireEvent.change(screen.getByRole('slider', { name: 'Size, upper bound' }), {
        target: { value: '500' },
      })
      fireEvent.change(screen.getByRole('slider', { name: 'Size, lower bound' }), {
        target: { value: '700' },
      })
      expect(
        (screen.getByRole('slider', { name: 'Size, lower bound' }) as HTMLInputElement).value,
      ).toBe('490')
    })
  })

  it('announces what each thumb means', () => {
    render(<Size />)
    expect(
      screen.getByRole('slider', { name: 'Size, lower bound' }).getAttribute('aria-valuetext'),
    ).toBe('no limit')
  })

  it('commits a typed bound on Enter or on leaving the field, not on every key', () => {
    render(<TypedBound />)
    const from = screen.getByRole('textbox', { name: 'Year, from' })
    fireEvent.change(from, { target: { value: '198' } })
    expect(TypedBound.args.exact?.onMin).not.toHaveBeenCalled()
    fireEvent.blur(from)
    expect(TypedBound.args.exact?.onMin).toHaveBeenCalledWith('198')
    fireEvent.change(screen.getByRole('textbox', { name: 'Year, to' }), {
      target: { value: '1999' },
    })
    fireEvent.keyDown(screen.getByRole('textbox', { name: 'Year, to' }), { key: 'Enter' })
    expect(TypedBound.args.exact?.onMax).toHaveBeenCalledWith('1999')
  })

  it('names its section by its title', () => {
    render(<Year />)
    expect(screen.getByRole('region', { name: 'Year' })).toBeTruthy()
  })
})
