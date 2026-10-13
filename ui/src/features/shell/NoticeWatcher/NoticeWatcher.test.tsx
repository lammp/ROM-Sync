import { composeStories } from '@storybook/react'
import { render, waitFor } from '@testing-library/react'
import { act } from 'react'
import { describe, expect, it, vi } from 'vitest'
import { answer } from '../../../../e2e/fake/world'
import { PROBE_MS } from '../../../queries/devices/devices'
import { appStore } from '../../../store/store'
import * as stories from './NoticeWatcher.stories'

const { SaysWhatHappens } = composeStories(stories)

const ids = () => appStore.getState().ui.notices.map((n) => n.id)

describe('NoticeWatcher', () => {
  it('lists the setup steps still to do, and takes one away once done', async () => {
    await SaysWhatHappens.load()
    render(<SaysWhatHappens />)
    await waitFor(() => expect(ids()).toEqual(['setup:igdb']))
    expect(appStore.getState().ui.toasts).toEqual([])
    answer(stories.worldNow(), 'POST', '/api/v1/settings', {
      values: { 'igdb.client_id': 'c', 'igdb.client_secret': 's3cr3tt' },
    })
    // the settings are read again when something asks; a scan's end does
    answer(stories.worldNow(), 'POST', '/api/v1/library/scan', {})
    await waitFor(() => expect(ids()[0]).toMatch(/^job:/))
  })

  it('says a job that ends while the page is open, once, as a toast and a notification', async () => {
    await SaysWhatHappens.load()
    render(<SaysWhatHappens />)
    await waitFor(() => expect(ids()).toContain('setup:igdb'))
    answer(stories.worldNow(), 'POST', '/api/v1/library/scan', {})
    await waitFor(() => expect(ids().filter((i) => i.startsWith('job:'))).toHaveLength(1))
    await new Promise((r) => setTimeout(r, 300))
    const said = appStore.getState().ui.toasts.filter((t) => t.text.startsWith('Scan finished'))
    expect(said).toHaveLength(1)
    expect(ids().filter((i) => i.startsWith('job:'))).toHaveLength(1)
  })

  it('adds a job that ended before the page loaded without a toast, and never one cleared', async () => {
    await SaysWhatHappens.load()
    answer(stories.worldNow(), 'POST', '/api/v1/library/scan', {})
    const old = stories.worldNow().jobs.at(-1)
    if (old) old.finished = '2020-01-01T00:00:00'
    render(<SaysWhatHappens />)
    await waitFor(() => expect(ids()).toContain(`job:${old?.id}`))
    expect(appStore.getState().ui.toasts).toEqual([])
    appStore.getState().ui.clearNotice(`job:${old?.id}`)
    await new Promise((r) => setTimeout(r, 300))
    expect(ids()).not.toContain(`job:${old?.id}`)
  })

  it('says a device pulled out and plugged back in, wherever the person is', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    try {
      await SaysWhatHappens.load()
      const world = stories.worldNow()
      render(<SaysWhatHappens />)
      await waitFor(() => expect(ids()).toContain('setup:igdb'))
      const thor = world.attached.find((a) => a.ref === world.profiles[0]?.ref)
      world.attached = world.attached.filter((a) => a !== thor)
      await act(() => vi.advanceTimersByTimeAsync(PROBE_MS))
      await waitFor(() =>
        expect(appStore.getState().ui.toasts.at(-1)?.text).toBe('Thor disconnected'),
      )
      if (thor) world.attached.push(thor)
      await act(() => vi.advanceTimersByTimeAsync(PROBE_MS))
      await waitFor(() => expect(appStore.getState().ui.toasts.at(-1)?.text).toBe('Thor connected'))
      const said = appStore.getState().ui.notices.filter((n) => n.source === 'device')
      expect(said.map((n) => n.title)).toEqual(['Thor connected', 'Thor disconnected'])
    } finally {
      vi.useRealTimers()
    }
  })
})
