import { composeStories } from '@storybook/react'
import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { FACET_TITLES } from './FilterSidebar'
import * as stories from './FilterSidebar.stories'

const { Default, NoDevice } = composeStories(stories)

describe('FilterSidebar', () => {
  it('has the nine facets, two range facets, smart lists, the rating, four flags and the chip list', () => {
    render(<Default />)
    for (const title of Object.values(FACET_TITLES))
      expect(screen.getByRole('region', { name: title }), title).toBeTruthy()
    expect(screen.getByRole('region', { name: 'Size' })).toBeTruthy()
    expect(screen.getByRole('region', { name: 'Year' })).toBeTruthy()
    expect(
      screen.getAllByRole('button', { name: /Top rated|Modern|Retro|Big games|RPGs|Platformers/ }),
    ).toHaveLength(6)
    expect(screen.getByRole('slider', { name: 'Rating at least' })).toBeTruthy()
    expect(screen.getAllByRole('checkbox')).toHaveLength(4)
    expect(screen.getByRole('group', { name: 'Filters in force' })).toBeTruthy()
  })

  it('reports a cleared facet, a fold and a flag', () => {
    render(<Default />)
    fireEvent.click(screen.getByRole('button', { name: 'Clear System' }))
    expect(Default.args.onClear).toHaveBeenCalledWith('system')
    fireEvent.click(screen.getByRole('button', { name: 'more… (+12)' }))
    expect(Default.args.onFold).toHaveBeenCalledWith('genre')
    fireEvent.click(screen.getByRole('checkbox', { name: 'multi-file games only' }))
    expect(Default.args.onFlag).toHaveBeenCalledWith('folder', true)
  })

  it('says the device flags need a device, and holds them off', () => {
    render(<NoDevice />)
    const flag = screen.getByRole('checkbox', {
      name: 'on this device now (choose a device)',
    }) as HTMLInputElement
    expect(flag.disabled).toBe(true)
  })
})
