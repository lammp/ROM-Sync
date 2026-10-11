import { formatBytes } from '../../../lib/format/format'
import { Button } from '../../atoms/Button/Button'
import { CoverImage } from '../../atoms/CoverImage/CoverImage'
import styles from './TwinRow.module.css'

export type TwinGame = {
  readonly title: string
  readonly name: string
  readonly sysLabel: string
  readonly year: number | null
  readonly size: number
  readonly cover: string | null
}

export type TwinAction =
  | { readonly kind: 'none' }
  /** This row is the game whose card it is. */
  | { readonly kind: 'self' }
  /** Already selected: kept as well. */
  | { readonly kind: 'kept' }
  /** Deselect the host's copy and select this one. */
  | { readonly kind: 'switch'; readonly from: string; readonly onSwitch: () => void }
  /** Select this version as well. */
  | { readonly kind: 'select'; readonly onSelect: () => void }

export type TwinRowProps = {
  readonly game: TwinGame
  readonly selected: boolean
  readonly onDevice: boolean
  readonly loose: boolean
  readonly action: TwinAction
  /** Opens this version; absent on the card's own row. */
  readonly onOpen?: () => void
}

/** One version in the compare card: what it is, where it stands, and what can be done with it. */
export function TwinRow({ game, selected, onDevice, loose, action, onOpen }: TwinRowProps) {
  const label = game.title || game.name
  const marks = [selected && 'selected', onDevice && 'on device'].filter(Boolean).join(' · ')
  return (
    <div className={[styles.row, action.kind === 'self' && styles.me].filter(Boolean).join(' ')}>
      <span className={styles.cover}>
        {game.cover ? <CoverImage src={game.cover} alt="" size="row" /> : null}
      </span>
      <span className={styles.meta}>
        {onOpen ? (
          <button type="button" className={styles.t} title={game.name} onClick={onOpen}>
            {label}
          </button>
        ) : (
          <span className={styles.t} title={game.name}>
            {label}
          </span>
        )}
        <span className={styles.s}>
          {game.sysLabel} · {game.year || '—'} · {formatBytes(game.size)}
        </span>
        <span className={styles.s}>
          {marks && <span className={styles.on}>{marks}</span>}
          {loose && <span className={styles.loose}>loose match</span>}
        </span>
      </span>
      <span className={styles.act}>
        {action.kind === 'self' && <span className={styles.muted}>this one</span>}
        {action.kind === 'kept' && <span className={styles.muted}>kept</span>}
        {action.kind === 'switch' && (
          <Button
            small
            onClick={action.onSwitch}
            title={`Deselect the ${action.from} copy and select this one instead`}
          >
            Switch
          </Button>
        )}
        {action.kind === 'select' && (
          <Button small onClick={action.onSelect} title="Select this version as well">
            Select
          </Button>
        )}
      </span>
    </div>
  )
}
