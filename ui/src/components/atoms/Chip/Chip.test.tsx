import { composeStories } from '@storybook/react'
import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import * as stories from './Chip.stories'

const { Plain, Clickable, Removable, EveryKind } = composeStories(stories)

describe('Chip', () => {
  it('is plain text unless it does something', () => {
    render(<Plain />)
    expect(screen.queryByRole('button')).toBeNull()
    expect(screen.getByText('Platformer')).toBeTruthy()
  })

  it('becomes a button when it acts', () => {
    render(<Clickable />)
    fireEvent.click(screen.getByRole('button', { name: 'SNES' }))
    expect(Clickable.args.onClick).toHaveBeenCalled()
  })

  it('names its remove button for what it removes', () => {
    render(<Removable />)
    fireEvent.click(screen.getByRole('button', { name: 'Remove Mario' }))
    expect(Removable.args.onRemove).toHaveBeenCalled()
  })

  it('draws all eight kinds', () => {
    render(<EveryKind />)
    for (const kind of [
      'plain',
      'system',
      'franchise',
      'suggested',
      'collection',
      'theme',
      'mode',
      'perspective',
    ])
      expect(screen.getByText(kind)).toBeTruthy()
  })
})
