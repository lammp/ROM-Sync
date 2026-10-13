import { useEffect, useId, useState } from 'react'
import { Button } from '../../atoms/Button/Button'
import { Icon } from '../../atoms/Icon/Icon'
import { formatEta } from '../../../lib/format/format'
import styles from './MetadataTracker.module.css'

export type Coverage = {
  readonly total: number
  readonly matched: number
  readonly pending: number
  readonly coverless: number
}

export type TrackedJob = {
  readonly state: string
  readonly progress: {
    readonly phase: string
    readonly done: number
    readonly total: number | null
    readonly current: string | null
  } | null
  readonly result: Readonly<Record<string, number>> | null
  readonly error: string | null
  /** When it started, as the engine records it. */
  readonly started: string | null
}

export type MetadataTrackerProps = {
  readonly coverage: Coverage
  /** The metadata job in view: running, or the last one this page saw end. */
  readonly job: TrackedJob | null
  readonly onStop?: () => void
}

const LIVE = new Set(['queued', 'running', 'cancelling'])
const PHASES: Readonly<Record<string, string>> = {
  match: 'Matching games',
  covers: 'Filling covers',
}
const R = 70
const ARC = 2 * Math.PI * R

/** A count with its word: "1 game", "7,311 games". */
const count = (n: number, one: string) => `${n.toLocaleString()} ${one}${n === 1 ? '' : 's'}`

/** Seconds left at the pace so far, or null while there is no pace yet. */
export function secondsLeft(
  done: number,
  total: number | null,
  started: string | null,
  now: number,
): number | null {
  if (!total || !started || done <= 0 || now <= 0) return null
  const elapsed = (now - Date.parse(started)) / 1000
  if (!Number.isFinite(elapsed) || elapsed <= 0) return null
  return ((total - done) * elapsed) / done
}

/** A clock that ticks every second while asked to, and reads 0 until its first tick. */
function useClock(on: boolean): number {
  const [now, setNow] = useState(0)
  useEffect(() => {
    if (!on) return
    const tick = () => setNow(Date.now())
    const timer = window.setInterval(tick, 1000)
    const first = window.setTimeout(tick, 0)
    return () => {
      window.clearInterval(timer)
      window.clearTimeout(first)
    }
  }, [on])
  return now
}

/**
 * The metadata's state as one graphic (F11-S53): at rest, a ring of how much
 * of the library is matched, with the counts beside it; while a pass runs,
 * the ring is its progress, turning, with the phase, the count, the game
 * being looked up, the time left and Stop; once it ends, how it went. Every
 * figure is also said in words, so neither the ring nor its colour carries
 * it alone.
 */
export function MetadataTracker({ coverage, job, onStop }: MetadataTrackerProps) {
  const live = job !== null && LIVE.has(job.state)
  const now = useClock(live)
  const gradient = `${useId()}-arc`
  const p = job?.progress ?? null
  const share = live
    ? p?.total
      ? p.done / p.total
      : 0
    : coverage.total
      ? coverage.matched / coverage.total
      : 0
  const percent = Math.round(Math.min(1, Math.max(0, share)) * 100)
  const phase = p ? (PHASES[p.phase] ?? p.phase) : 'Starting'
  const left = live && p ? secondsLeft(p.done, p.total, job.started, now) : null
  const ended = job !== null && !live ? job.state : null
  const tone = live ? 'running' : ended === 'failed' ? 'failed' : ended === 'done' ? 'done' : 'rest'
  const words = live
    ? job.state === 'cancelling'
      ? 'Stopping'
      : `${phase}${p?.total ? `: ${p.done.toLocaleString()} of ${p.total.toLocaleString()}` : ''}`
    : `${percent}% of the library matched`
  return (
    <section className={styles.tracker} data-tone={tone} aria-label="Metadata progress">
      <div
        className={styles.ring}
        role={live ? 'progressbar' : 'img'}
        aria-label={live ? phase : words}
        aria-valuemin={live ? 0 : undefined}
        aria-valuemax={live ? 100 : undefined}
        aria-valuenow={live ? percent : undefined}
        aria-valuetext={live ? words : undefined}
      >
        <svg viewBox="0 0 160 160" aria-hidden="true" focusable="false">
          <defs>
            <linearGradient id={gradient} x1="0" y1="0" x2="1" y2="1">
              <stop offset="0%" className={styles.from} />
              <stop offset="100%" className={styles.to} />
            </linearGradient>
          </defs>
          <circle className={styles.track} cx="80" cy="80" r={R} />
          <circle
            className={styles.fill}
            stroke={tone === 'running' || tone === 'rest' ? `url(#${gradient})` : undefined}
            cx="80"
            cy="80"
            r={R}
            strokeDasharray={`${(ARC * percent) / 100} ${ARC}`}
          />
          {live && <circle className={styles.sweep} cx="80" cy="80" r={R} />}
        </svg>
        <span className={styles.centre}>
          {ended === 'done' ? (
            <Icon name="tick" size={36} tone="ok" />
          ) : ended === 'failed' ? (
            <Icon name="cross" size={36} tone="bad" />
          ) : (
            <b className={styles.percent}>{percent}%</b>
          )}
          <span className={styles.caption}>
            {live
              ? 'done'
              : ended === 'done'
                ? 'finished'
                : ended === 'failed'
                  ? 'failed'
                  : 'matched'}
          </span>
        </span>
      </div>
      <div className={styles.facts}>
        {live ? (
          <>
            <b className={styles.phase}>{words}</b>
            {p?.current && <span className={styles.current}>{p.current}</span>}
            <span className={styles.left}>
              {left !== null ? `about ${formatEta(left)} left` : 'working out the time left…'}
            </span>
          </>
        ) : ended === 'failed' ? (
          <b className={styles.phase}>
            Stopped: {(job?.error ?? 'no reason given').split('\n')[0]}
          </b>
        ) : ended === 'cancelled' ? (
          <b className={styles.phase}>Stopped before the end</b>
        ) : ended === 'done' && job?.result ? (
          <b className={styles.phase}>
            {job.result.no_credentials
              ? `${count(job.result.filled ?? 0, 'cover')} filled; matching needs credentials`
              : `${count(job.result.matched ?? 0, 'game')} matched, ${count(job.result.filled ?? 0, 'cover')} filled`}
          </b>
        ) : (
          <b className={styles.phase}>{words}</b>
        )}
      </div>
      <dl className={styles.counts}>
        <div data-kind="matched">
          <dt>Matched</dt>
          <dd>{coverage.matched.toLocaleString()}</dd>
        </div>
        <div data-kind="pending">
          <dt>Not looked up</dt>
          <dd>{coverage.pending.toLocaleString()}</dd>
        </div>
        <div data-kind="coverless">
          <dt>Without a cover</dt>
          <dd>{coverage.coverless.toLocaleString()}</dd>
        </div>
      </dl>
      {live && onStop && (
        <Button disabled={job.state === 'cancelling'} onClick={onStop}>
          Stop
        </Button>
      )}
    </section>
  )
}
