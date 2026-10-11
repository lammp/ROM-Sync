import { composeStories } from '@storybook/react'
import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import * as stories from './DevicePicker.stories'

const { Online, None } = composeStories(stories)

describe('DevicePicker', () => {
  it('offers no device and every profile, offline ones said so', () => {
    render(<Online />)
    expect(screen.getAllByRole('option').map((o) => o.textContent)).toEqual([
      'No device',
      'Thor',
      'Card (offline)',
    ])
    fireEvent.change(screen.getByRole('combobox', { name: 'Device' }), {
      target: { value: 'dev-2' },
    })
    expect(Online.args.onChange).toHaveBeenCalledWith('dev-2')
  })

  it('draws no lamp without a device', () => {
    render(<None />)
    expect(screen.queryByRole('img')).toBeNull()
  })
})
