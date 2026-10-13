import { composeStories } from '@storybook/react'
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import * as stories from './LinkButton.stories'

const { Download } = composeStories(stories)

describe('LinkButton', () => {
  it('is a link that saves a file, with its glyph', () => {
    render(<Download />)
    const link = screen.getByRole('link', { name: 'Export a support bundle' })
    expect(link.getAttribute('href')).toBe('/api/v1/diagnostics/bundle')
    expect(link.getAttribute('download')).toBe('romsync-support.zip')
    expect(link.querySelector('svg')?.getAttribute('data-icon')).toBe('download')
  })
})
