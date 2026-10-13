import { composeStories } from '@storybook/react'
import { render } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { ICONS } from './Icon'
import * as stories from './Icon.stories'

const { Edit, Turning, All } = composeStories(stories)

describe('Icon', () => {
  it('is decoration, hidden from assistive technology', () => {
    const { container } = render(<Edit />)
    const svg = container.querySelector('svg')
    expect(svg?.getAttribute('aria-hidden')).toBe('true')
    expect(svg?.getAttribute('focusable')).toBe('false')
  })

  it('turns only when asked', () => {
    const { container } = render(<Turning />)
    expect(container.querySelector('svg')?.getAttribute('class')).toMatch(/turning/)
  })

  it('draws every glyph it names', () => {
    const { container } = render(<All />)
    const drawn = [...container.querySelectorAll('svg')].map((s) => s.getAttribute('data-icon'))
    expect(drawn).toEqual(ICONS)
    for (const path of container.querySelectorAll('path'))
      expect(path.getAttribute('d')).toMatch(/^M/)
  })
})
