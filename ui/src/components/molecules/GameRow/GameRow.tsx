import { formatBytes } from '../../../lib/format/format'
import { CoverImage } from '../../atoms/CoverImage/CoverImage'
import { SelectionBadge } from '../../atoms/SelectionBadge/SelectionBadge'
import { TwinGlyph } from '../../atoms/TwinGlyph/TwinGlyph'
import type { TileDevice, TileGame, TileTwin } from '../GameTile/GameTile'
import styles from './GameRow.module.css'

export type RowGame = TileGame & { readonly sysLabel: string; readonly size: number }

export type GameRowProps = {
  readonly game: RowGame
  readonly current: boolean
  readonly onOpen: () => void
  readonly device?: TileDevice
  readonly twin?: TileTwin
}

/** One game in the list view: the same four badges as a tile, with the figures in columns. */
export function GameRow({ game, current, onOpen, device, twin }: GameRowProps) {
  const label = game.title || game.name
  return (
    <div className={[styles.lrow, current && styles.current].filter(Boolean).join(' ')}>
      <span>
        {device && (
          <SelectionBadge
            selected={device.selected}
            override={device.override}
            title={label}
            device={device.name}
            onToggle={device.onToggle}
          />
        )}
      </span>
      <span>{game.cover ? <CoverImage src={game.cover} alt="" size="row" /> : null}</span>
      <button
        type="button"
        className={styles.open}
        aria-current={current ? 'true' : undefined}
        title={game.name}
        onClick={onOpen}
      >
        <span className={styles.t}>{label}</span>
        {device?.onDevice && <span className={styles.ondev}>on device</span>}
      </button>
      <span className={styles.badges}>
        {twin && <TwinGlyph dupe={twin.dupe} label={twin.label} />}
      </span>
      <span className={styles.muted}>{game.sysLabel}</span>
      <span className={styles.num}>{game.year || ''}</span>
      <span className={styles.num}>{game.rating || ''}</span>
      <span className={[styles.num, styles.muted].join(' ')}>{formatBytes(game.size)}</span>
    </div>
  )
}
