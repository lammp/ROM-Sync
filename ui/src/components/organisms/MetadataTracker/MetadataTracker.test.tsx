import { composeStories } from '@storybook/react'
import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { secondsLeft, status } from './MetadataTracker'
import * as stories from './MetadataTracker.stories'

const { AtRest, Running, Covers, Finished, Failed, Stopped } = composeStories(stories)

describe('MetadataTracker', () => {
  it('shows how much of the library is matched at rest, in words as well as the ring', () => {
    render(<AtRest />)
    expect(screen.getByRole('img', { name: '7% of the library matched' })).toBeTruthy()
    expect(screen.getByText('7,311')).toBeTruthy()
    expect(screen.getByText('Not looked up')).toBeTruthy()
    expect(screen.getByText('of games matched')).toBeTruthy()
    expect(screen.getByText('Not matched').nextElementSibling?.textContent).toBe('38')
  })

  it('shows a running pass as progress, with the game, and offers Stop', () => {
    render(<Running />)
    const ring = screen.getByRole('progressbar', { name: 'Matching games' })
    expect(ring.getAttribute('aria-valuenow')).toBe('17')
    expect(ring.getAttribute('aria-valuetext')).toBe('Matching games: 1,234 of 7,311')
    expect(screen.getByText('Chrono Trigger')).toBeTruthy()
    expect(document.querySelector('section')?.getAttribute('data-tone')).toBe('running')
    fireEvent.click(screen.getByRole('button', { name: 'Stop' }))
    expect(Running.args.onStop).toHaveBeenCalledOnce()
  })

  it('names the cover phase', () => {
    render(<Covers />)
    expect(screen.getByRole('progressbar', { name: 'Filling covers' })).toBeTruthy()
  })

  it('says how a pass ended, with a tick or a cross', () => {
    const done = render(<Finished />)
    // a finished run is a full ring, never the library's coverage
    expect(screen.getByRole('img', { name: 'Run complete' })).toBeTruthy()
    expect(document.querySelector('[class*="fill"]')?.getAttribute('stroke-dasharray')).toMatch(
      /^439\.8/,
    )
    expect(screen.getByText('7,311 games looked up: 7,100 matched, 211 not')).toBeTruthy()
    expect(screen.getByText('320 covers filled')).toBeTruthy()
    expect(screen.getByText('92% of the library matched')).toBeTruthy()
    expect(screen.getByText('Not matched').nextElementSibling?.textContent).toBe('631')
    const tick = screen
      .getByRole('img', { name: 'Run complete' })
      .querySelector('[data-icon="tick"]')
    expect(tick).not.toBeNull()
    // the tick is an icon in the ring, not drawn as the ring: it keeps its size and is not turned
    expect(tick?.getAttribute('width')).toBe('36')
    expect(tick?.getAttribute('class') ?? '').not.toMatch(/dial/)
    done.unmount()
    render(<Failed />)
    expect(screen.getByText(/^Stopped: stopped after 25 failures/)).toBeTruthy()
    expect(
      screen.getByRole('img', { name: 'Run failed' }).querySelector('[data-icon="cross"]'),
    ).not.toBeNull()
  })

  it('works out the time left from the pace so far', () => {
    const started = '2026-10-13T10:00:00Z'
    const tenMinutesIn = Date.parse(started) + 600_000
    expect(secondsLeft(100, 400, started, tenMinutesIn)).toBe(1800)
    expect(secondsLeft(0, 400, started, tenMinutesIn)).toBeNull()
    expect(secondsLeft(10, null, started, tenMinutesIn)).toBeNull()
    expect(secondsLeft(10, 40, null, tenMinutesIn)).toBeNull()
    expect(secondsLeft(10, 40, started, 0)).toBeNull()
  })

  it('says which view it is: not run, running, complete, failed or stopped, with when', () => {
    const shown = (Story: typeof AtRest) => {
      const { container, unmount } = render(<Story />)
      const badge = container.querySelector('[data-status]')
      const out = [badge?.getAttribute('data-status'), badge?.textContent ?? '']
      unmount()
      return out
    }
    expect(shown(AtRest)).toEqual(['none', 'Not run yet'])
    expect(shown(Running)[0]).toBe('running')
    expect(shown(Running)[1]).toMatch(/^Running since \d{1,2} Oct/)
    expect(shown(Covers)).toEqual(['running', 'Running'])
    expect(shown(Finished)[1]).toMatch(/^Complete · \d{1,2} Oct/)
    expect(shown(Failed)[1]).toMatch(/^Failed · /)
    expect(shown(Stopped)[1]).toMatch(/^Stopped · /)
    expect(
      status({
        state: 'cancelling',
        progress: null,
        result: null,
        error: null,
        started: null,
        finished: null,
      }).words,
    ).toBe('Stopping')
  })
})
