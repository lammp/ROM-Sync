import { useEffect, useId, useRef, useState } from 'react'
import { ActionLink } from '../../atoms/ActionLink/ActionLink'
import { Dot } from '../../atoms/Dot/Dot'
import { IconButton } from '../../atoms/IconButton/IconButton'
import styles from './NotificationCentre.module.css'

export type NotificationItem = {
  readonly id: string
  readonly tone: 'info' | 'warn' | 'bad'
  readonly title: string
  readonly body?: string
  /** When it happened, in milliseconds. */
  readonly at: number
  readonly read: boolean
  readonly href?: string
}

export type NotificationCentreProps = {
  /** Newest first. */
  readonly notices: readonly NotificationItem[]
  /** The list was opened: everything in it is now read. */
  readonly onOpen: () => void
  readonly onClear: (id: string) => void
  readonly onClearAll: () => void
  /** Goes where a notification points. */
  readonly onFollow: (href: string) => void
  /** The time now, for saying when; the clock unless a story fixes it. */
  readonly now?: number
}

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

/** When, as the list says it: the time today, the day and time before ("12 Oct 09:05"). */
export function when(at: number, now: number): string {
  const then = new Date(at)
  const time = then.toTimeString().slice(0, 5)
  return then.toDateString() === new Date(now).toDateString()
    ? time
    : `${then.getDate()} ${MONTHS[then.getMonth()]} ${time}`
}

const TONE = { info: 'neutral', warn: 'warn', bad: 'bad' } as const
const WORD = { info: '', warn: 'Warning: ', bad: 'Error: ' } as const

/**
 * The notification bell (F11-S47). It shows how many are unread, and opens a
 * list of what happened, newest first, each clearable, with Clear all. The
 * list closes on its close button, Escape, a click outside, or the bell.
 */
export function NotificationCentre({
  notices,
  onOpen,
  onClear,
  onClearAll,
  onFollow,
  now,
}: NotificationCentreProps) {
  const [open, setOpen] = useState(false)
  // read when the list opens, in the handler, so rendering stays pure
  const [openedAt, setOpenedAt] = useState(0)
  const panelId = useId()
  const headId = useId()
  const root = useRef<HTMLDivElement>(null)
  const unread = notices.filter((n) => !n.read).length

  const close = () => {
    setOpen(false)
    root.current?.querySelector<HTMLButtonElement>('button[aria-controls]')?.focus()
  }

  useEffect(() => {
    if (open) root.current?.querySelector<HTMLElement>('[role="dialog"]')?.focus()
  }, [open])

  useEffect(() => {
    if (!open) return
    const outside = (e: MouseEvent) => {
      if (e.target instanceof Node && !root.current?.contains(e.target)) setOpen(false)
    }
    document.addEventListener('mousedown', outside)
    return () => document.removeEventListener('mousedown', outside)
  }, [open])

  return (
    <div ref={root} className={styles.centre}>
      <IconButton
        label={unread ? `Notifications, ${unread} unread` : 'Notifications'}
        aria-expanded={open}
        aria-controls={panelId}
        active={open}
        onClick={() => {
          if (open) close()
          else {
            setOpenedAt(Date.now())
            setOpen(true)
            onOpen()
          }
        }}
      >
        <svg className={styles.bell} viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
          <path
            fill="currentColor"
            d="M12 22a2.5 2.5 0 0 0 2.45-2h-4.9A2.5 2.5 0 0 0 12 22Zm7-6V11a7 7 0 0 0-5.5-6.84V3.5a1.5 1.5 0 0 0-3 0v.66A7 7 0 0 0 5 11v5l-2 2v1h18v-1l-2-2Z"
          />
        </svg>
        {unread > 0 && (
          <span className={styles.count} aria-hidden="true">
            {unread > 99 ? '99+' : unread}
          </span>
        )}
      </IconButton>
      {open && (
        <div
          id={panelId}
          className={styles.panel}
          role="dialog"
          aria-labelledby={headId}
          tabIndex={-1}
          onKeyDown={(e) => {
            if (e.key === 'Escape') {
              e.stopPropagation()
              close()
            }
          }}
        >
          <div className={styles.top}>
            <h2 id={headId} className={styles.head}>
              Notifications
            </h2>
            {notices.length > 0 && <ActionLink onClick={onClearAll}>Clear all</ActionLink>}
            <IconButton label="Close" onClick={close}>
              ×
            </IconButton>
          </div>
          {notices.length === 0 ? (
            <p className={styles.empty}>Nothing to report.</p>
          ) : (
            <ul className={styles.list} aria-labelledby={headId}>
              {notices.map((n) => (
                <li key={n.id} className={styles.item}>
                  <Dot tone={TONE[n.tone]} />
                  <div className={styles.text}>
                    <p className={styles.title}>
                      {WORD[n.tone] && <span className={styles.hidden}>{WORD[n.tone]}</span>}
                      {n.title}
                    </p>
                    {n.body && <p className={styles.body}>{n.body}</p>}
                    <p className={styles.meta}>
                      <time dateTime={new Date(n.at).toISOString()}>
                        {when(n.at, now ?? openedAt)}
                      </time>
                      {n.href && (
                        <>
                          {' · '}
                          <ActionLink
                            onClick={() => {
                              setOpen(false)
                              onFollow(n.href as string)
                            }}
                          >
                            Open
                          </ActionLink>
                        </>
                      )}
                    </p>
                  </div>
                  <IconButton label={`Clear ${n.title}`} onClick={() => onClear(n.id)}>
                    ×
                  </IconButton>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  )
}
