import { composeStories } from '@storybook/react'
import { render, screen } from '@testing-library/react'
import { expect, it } from 'vitest'
import * as stories from './PlanDetailList.stories'

const { Three } = composeStories(stories)

it('lists each operation with its verb, path and size', () => {
  render(<Three />)
  expect(screen.getAllByRole('listitem').map((li) => li.textContent)).toEqual([
    'send snes \\ Super Metroid.sfc 3.00 MB',
    'replace gba \\ Metroid Fusion.gba 8.00 MB',
    'remove nes \\ Metroid.nes 128.0 KB',
  ])
})
