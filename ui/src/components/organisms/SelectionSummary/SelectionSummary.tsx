import { useEffect, type ReactNode } from 'react'
import { formatBytes } from '../../../lib/format/format'
import { Button } from '../../atoms/Button/Button'
import { TextLink } from '../../atoms/TextLink/TextLink'
import styles from './SelectionSummary.module.css'

/** How long the selection must stay still before the capacity is read again. */
export const CAPACITY_SETTLE_MS = 250

export type SelectionSummaryProps = {
  readonly device: { readonly name: string; readonly href: string }
  readonly selected: { readonly n: number; readonly bytes: number }
  /** Games on the device now; system files under bios are not games and are not counted. */
  readonly onDevice: number
  /** Of the games shown, how many are selected and how many are not. */
  readonly shown: { readonly selected: number; readonly unselected: number }
  readonly sync: ReactNode
  readonly onClearShown: () => void
  readonly onSelectShown: () => void
  readonly onClearAll: () => void
  /** Changes whenever the selection does. */
  readonly selectionKey: unknown
  /** Called once the selection has been still for 250 ms, to read the capacity again. */
  readonly onSettled: () => void
}

/** The device in view, what is selected for it, the sync control, and the bulk actions. */
export function SelectionSummary(p: SelectionSummaryProps) {
  const { selectionKey, onSettled } = p
  useEffect(() => {
    const timer = setTimeout(onSettled, CAPACITY_SETTLE_MS)
    return () => clearTimeout(timer)
  }, [selectionKey, onSettled])
  return (
    <div className={styles.summary} role="group" aria-label={`Selection for ${p.device.name}`}>
      <TextLink href={p.device.href}>{p.device.name}</TextLink>
      <span>
        <b>{p.selected.n.toLocaleString()}</b> selected ({formatBytes(p.selected.bytes)}) ·{' '}
        <span>{p.onDevice.toLocaleString()} on device</span>
      </span>
      {p.sync}
      <Button small disabled={!p.shown.selected} onClick={p.onClearShown}>
        Clear shown{p.shown.selected ? ` (${p.shown.selected.toLocaleString()})` : ''}
      </Button>
      <Button small disabled={!p.shown.unselected} onClick={p.onSelectShown}>
        Select shown{p.shown.unselected ? ` (${p.shown.unselected.toLocaleString()})` : ''}
      </Button>
      <Button small variant="danger" disabled={!p.selected.n} onClick={p.onClearAll}>
        Clear all
      </Button>
    </div>
  )
}
