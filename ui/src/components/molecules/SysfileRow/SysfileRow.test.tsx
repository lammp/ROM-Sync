import { composeStories } from '@storybook/react'
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { READINESS } from './SysfileRow'
import * as stories from './SysfileRow.stories'

const { Ready, Active, NoGames } = composeStories(stories)

describe('SysfileRow', () => {
  it('writes its readiness in a word beside the dot', () => {
    render(<Ready />)
    expect(screen.getByRole('button').textContent).toContain('ready')
    expect(Object.values(READINESS).map(([, w]) => w)).toEqual([
      'ready',
      'missing',
      'optional',
      'nothing needed',
      'not seen over USB',
      'not scanned',
    ])
  })

  it('marks the system shown in the detail', () => {
    render(<Active />)
    expect(screen.getByRole('button').getAttribute('aria-current')).toBe('true')
  })

  it('says when the device has none of its games', () => {
    render(<NoGames />)
    expect(screen.getByText('no games')).toBeTruthy()
  })
})
