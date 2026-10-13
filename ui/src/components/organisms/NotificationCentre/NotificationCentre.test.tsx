import { composeStories } from '@storybook/react'
import { fireEvent, render, screen, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { when } from './NotificationCentre'
import * as stories from './NotificationCentre.stories'

const { Unread, Empty } = composeStories(stories)

describe('NotificationCentre', () => {
  it('counts the unread on the bell, and opening it reads them', () => {
    render(<Unread />)
    const bell = screen.getByRole('button', { name: 'Notifications, 2 unread' })
    expect(bell.textContent).toContain('2')
    fireEvent.click(bell)
    expect(Unread.args.onOpen).toHaveBeenCalledOnce()
    expect(within(screen.getByRole('dialog')).getAllByRole('listitem')).toHaveLength(3)
  })

  it('closes on a click outside', () => {
    render(<Unread />)
    fireEvent.click(screen.getByRole('button', { name: /^Notifications/ }))
    fireEvent.mouseDown(screen.getByRole('dialog'))
    expect(screen.queryByRole('dialog')).not.toBeNull()
    fireEvent.mouseDown(document.body)
    expect(screen.queryByRole('dialog')).toBeNull()
  })

  it('has no count with nothing to report', () => {
    render(<Empty />)
    expect(screen.getByRole('button', { name: 'Notifications' }).textContent).toBe('')
  })

  it('says when: the time today, the day before', () => {
    const now = new Date(2026, 9, 13, 14, 30).getTime()
    expect(when(new Date(2026, 9, 13, 9, 5).getTime(), now)).toBe('09:05')
    expect(when(new Date(2026, 9, 12, 9, 5).getTime(), now)).toMatch(
      /12.*Oct.*09:05|Oct.*12.*09:05/,
    )
  })
})
