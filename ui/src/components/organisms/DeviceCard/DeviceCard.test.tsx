import { composeStories } from '@storybook/react'
import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { seenAt, type CandidateCard, type ProfileCard } from './DeviceCard'
import * as stories from './DeviceCard.stories'

const { ProfileOnline, ProfileOffline, CandidateNew, CandidateForeign, CandidateDebugging } =
  composeStories(stories)

describe('DeviceCard', () => {
  it('shows a profile online: where its ROMs are, its space, its figures and three actions', () => {
    render(<ProfileOnline />)
    const card = screen.getByRole('article', { name: 'Thor' })
    expect(card.textContent).toContain('online · ADB · ROMs at /storage/emulated/0/ROMs')
    expect(card.textContent).toContain('120.0 GB free of 256.0 GB')
    expect(screen.getByRole('meter', { name: 'Space used' })).toBeTruthy()
    expect(card.textContent).toContain('1,204')
    const args = ProfileOnline.args as ProfileCard
    for (const [name, spy] of [
      ['Sync', args.onSync],
      ['Contents', args.onContents],
      ['Choose games', args.onChoose],
    ] as const) {
      fireEvent.click(screen.getByRole('button', { name }))
      expect(spy).toHaveBeenCalledTimes(1)
    }
  })

  it('shows a profile offline: when it was last seen, and no sync', () => {
    render(<ProfileOffline />)
    expect(screen.getByRole('img', { name: 'Thor is not connected' })).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Sync' }).hasAttribute('disabled')).toBe(true)
    expect(screen.getByText('capacity unknown')).toBeTruthy()
  })

  it('offers a new profile for a device with none', () => {
    render(<CandidateNew />)
    expect(screen.getByText('drive')).toBeTruthy()
    expect(screen.getByText('no profile yet')).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: 'New profile…' }))
    const state = (CandidateNew.args as CandidateCard).state
    expect(state.kind === 'new' && state.onNew).toHaveBeenCalledTimes(1)
  })

  it('offers to adopt a device carrying another computer’s marker', () => {
    render(<CandidateForeign />)
    expect(screen.getByText('carries ROM-Sync.json from another computer')).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Adopt profile' })).toBeTruthy()
  })

  it('says why a device cannot be read, and what to do on it, with nothing to press', () => {
    render(<CandidateDebugging />)
    expect(screen.getByText('unauthorized: accept the debugging prompt on the device')).toBeTruthy()
    expect(screen.queryByRole('button')).toBeNull()
  })

  it('writes last seen to the minute, and never for nothing', () => {
    expect([seenAt('2026-10-10T10:00:59'), seenAt('')]).toEqual(['2026-10-10 10:00', 'never'])
  })
})
