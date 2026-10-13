import { composeStories } from '@storybook/react'
import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import * as stories from './SyncControl.stories'

const { Idle, NotConnected, Starting, Running } = composeStories(stories)

describe('SyncControl', () => {
  it('idle: a primary Sync button', () => {
    render(<Idle />)
    fireEvent.click(screen.getByRole('button', { name: 'Sync' }))
    const state = Idle.args.state
    if (state?.kind === 'idle') expect(state.onSync).toHaveBeenCalled()
  })

  it('disabled: the button cannot be pressed and the reason is written beside it', () => {
    render(<NotConnected />)
    expect((screen.getByRole('button', { name: 'Sync' }) as HTMLButtonElement).disabled).toBe(true)
    expect(screen.getByText('Plug the device in to sync')).toBeTruthy()
  })

  it('running: a status with the percentage, the estimate and the phase', () => {
    render(<Running />)
    const status = screen.getByRole('status')
    expect(status.textContent).toContain('42%')
    expect(status.textContent).toContain('ETA 2 min')
    expect(status.getAttribute('title')).toContain('1.00 MB/s')
    expect(screen.queryByRole('button')).toBeNull()
  })

  it('says it is starting before the first poll', () => {
    render(<Starting />)
    expect(screen.getByRole('status').textContent).toContain('starting…')
  })
})
