import { CoverImage } from '../../atoms/CoverImage/CoverImage'
import { NoCover } from '../../atoms/NoCover/NoCover'
import { SelectionBadge } from '../../atoms/SelectionBadge/SelectionBadge'
import { TwinGlyph } from '../../atoms/TwinGlyph/TwinGlyph'
import styles from './GameTile.module.css'

export type TileGame = {
  readonly id: number
  readonly title: string
  readonly name: string
  readonly system: string
  readonly year: number | null
  readonly rating: number | null
  /** The cover's address, or null for the titled placeholder. */
  readonly cover: string | null
}

/** The device in view: its name, and this game's place on it. */
export type TileDevice = {
  readonly name: string
  readonly selected: boolean
  readonly override: boolean
  readonly onDevice: boolean
  readonly onToggle: () => void
}

export type TileTwin = {
  readonly dupe: boolean
  readonly label: string
  /** Opens the compare card; offered on the selected tile only. */
  readonly onCompare?: () => void
}

export type GameTileProps = {
  readonly game: TileGame
  /** The game the detail panel shows. */
  readonly current: boolean
  readonly onOpen: () => void
  /** Present when a device is chosen: the selection badge and the on-device badge. */
  readonly device?: TileDevice
  /** Present when the game exists on another system. */
  readonly twin?: TileTwin
}

/** One game in the grid: its cover, its caption, and up to four badges. */
export function GameTile({ game, current, onOpen, device, twin }: GameTileProps) {
  const label = game.title || game.name
  const facts = [game.year, game.rating].filter((x) => x != null && x !== 0)
  return (
    <div className={[styles.tile, current && styles.current].filter(Boolean).join(' ')}>
      <button
        type="button"
        className={styles.open}
        aria-current={current ? 'true' : undefined}
        title={game.name}
        onClick={onOpen}
      >
        <span aria-hidden="true">
          {game.cover ? <CoverImage src={game.cover} alt="" /> : <NoCover title={label} />}
        </span>
        <span className={styles.cap}>
          <span className={styles.t}>{label}</span>{' '}
          <span className={styles.s}>
            <span>{game.system}</span> <span>{facts.join(' · ')}</span>
          </span>
        </span>
      </button>
      {device && (
        <span className={styles.sel}>
          <SelectionBadge
            selected={device.selected}
            override={device.override}
            title={label}
            device={device.name}
            onToggle={device.onToggle}
          />
        </span>
      )}
      {twin && (
        <span className={styles.twin}>
          {current && twin.onCompare ? (
            <button
              type="button"
              className={styles.compare}
              aria-label={`Compare versions: ${twin.label}`}
              onClick={twin.onCompare}
            >
              <TwinGlyph dupe={twin.dupe} label={twin.label} />
            </button>
          ) : (
            <TwinGlyph dupe={twin.dupe} label={twin.label} />
          )}
        </span>
      )}
      {device?.onDevice && (
        <span className={[styles.ondev, twin && styles.below].filter(Boolean).join(' ')}>
          on device
        </span>
      )}
    </div>
  )
}
