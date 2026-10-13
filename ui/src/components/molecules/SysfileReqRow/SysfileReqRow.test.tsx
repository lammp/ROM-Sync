import { composeStories } from '@storybook/react'
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import * as stories from './SysfileReqRow.stories'

const { AllGood, Missing, Different } = composeStories(stories)

describe('SysfileReqRow', () => {
  it('says each of the three state vocabularies in words', () => {
    render(<Missing />)
    for (const word of ['not in store', 'not staged', 'not installed'])
      expect(screen.getByText(word)).toBeTruthy()
  })

  it('names a verified store copy by size', () => {
    render(<AllGood />)
    expect(screen.getByText('512.0 KB verified')).toBeTruthy()
    expect(screen.getByText('required')).toBeTruthy()
  })

  it('shows the staged name, the group and an unknown dump', () => {
    render(<Different />)
    expect(screen.getByText('bios.bin')).toBeTruthy()
    expect(screen.getByText('(any one)')).toBeTruthy()
    expect(screen.getByText('512.0 KB not a known dump')).toBeTruthy()
    expect(screen.getByText('different version')).toBeTruthy()
  })
})
