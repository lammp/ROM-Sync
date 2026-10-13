import { formatBytes } from '../../../lib/format/format'
import styles from './DeviceFigures.module.css'

export type DeviceFiguresProps = {
  readonly selected: number
  readonly onDevice: number
  readonly usedByGames: number
}

/** A device card's three figures. */
export function DeviceFigures({ selected, onDevice, usedByGames }: DeviceFiguresProps) {
  const figures = [
    ['selected', selected.toLocaleString()],
    ['on device', onDevice.toLocaleString()],
    ['used by games', formatBytes(usedByGames)],
  ] as const
  return (
    <dl className={styles.figs}>
      {figures.map(([label, value]) => (
        <div key={label}>
          <dt>{label}</dt>
          <dd>{value}</dd>
        </div>
      ))}
    </dl>
  )
}
