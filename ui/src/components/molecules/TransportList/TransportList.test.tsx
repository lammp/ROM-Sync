import { composeStories } from '@storybook/react'
import { render, screen, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import * as stories from './TransportList.stories'

const { AllFound, WithoutAdb, NotAskedYet } = composeStories(stories)

const lines = () =>
  within(screen.getByRole('list', { name: 'Detected transports' }))
    .getAllByRole('listitem')
    .map((li) => li.textContent)

describe('TransportList', () => {
  it('names each transport, whether it was asked, and what it said', () => {
    render(<AllFound />)
    expect(lines()).toEqual([
      'Drivesavailable2 drive(s)',
      'MTPavailable1 storage(s)',
      'ADBavailable1 device(s)',
    ])
  })

  it('says an absent tool or a transport turned off in words, never colour alone', () => {
    render(<WithoutAdb />)
    expect(lines()).toEqual([
      'Drivesavailable2 drive(s)',
      'MTPnot availableturned off in Settings',
      'ADBnot availablethe Android debug bridge (adb) was not found on the PATH',
    ])
  })

  it('says nothing before the first probe answers', () => {
    const { container } = render(<NotAskedYet />)
    expect(container.textContent).toBe('')
  })
})
