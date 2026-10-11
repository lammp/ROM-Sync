import { useState, type ReactNode } from 'react'
import { formatBytes } from '../../../lib/format/format'
import { Button } from '../../atoms/Button/Button'
import { CoverImage } from '../../atoms/CoverImage/CoverImage'
import { IconButton } from '../../atoms/IconButton/IconButton'
import { KeyValueText } from '../../atoms/KeyValueText/KeyValueText'
import { NoCover } from '../../atoms/NoCover/NoCover'
import { TextInput } from '../../atoms/TextInput/TextInput'
import { TagAdd, type NewTag } from '../../molecules/TagAdd/TagAdd'
import { TagChipGroup, type Tag } from '../../molecules/TagChipGroup/TagChipGroup'
import { VersionPicker, type Version } from '../../molecules/VersionPicker/VersionPicker'
import styles from './DetailPanel.module.css'

export type DetailGame = {
  readonly id: number
  readonly title: string
  readonly name: string
  readonly cover: string | null
  readonly year: number | null
  readonly rating: number | null
  readonly votes: number | null
  readonly size: number
  readonly kind: string
  readonly files: number
  readonly regions: readonly string[]
  readonly summary: string | null
  readonly matched: boolean
  readonly igdbName: string | null
  readonly confidence: number | null
  readonly genres: readonly string[]
}

export type DetailPanelProps = {
  readonly game: DetailGame
  readonly versions: readonly Version[]
  readonly onPickVersion: (id: number) => void
  /** Present when a device is chosen. */
  readonly device?: {
    readonly name: string
    readonly selected: boolean
    readonly onToggle: () => void
  }
  readonly tags: readonly Tag[]
  readonly onRemoveTag: (tag: Tag) => void
  readonly onDecideTag: (tag: Tag, accept: boolean) => void
  readonly onAddTag: (tag: NewTag) => void
  /** Pins the game to a metadata entry by id, slug or link. */
  readonly onRematch: (ref: string) => void
  /** The rematch job's line, while one runs or after. */
  readonly rematch?: ReactNode
  readonly onClose: () => void
}

/** One game in full: what it is, its tags, its versions, and the actions on it. */
export function DetailPanel(p: DetailPanelProps) {
  const g = p.game
  const label = g.title || g.name
  const [ref, setRef] = useState('')
  return (
    <article className={styles.detail} aria-labelledby={`game-${g.id}`}>
      <div className={styles.close}>
        <IconButton label="Close details" onClick={p.onClose}>
          ×
        </IconButton>
      </div>
      {g.cover ? (
        <CoverImage src={g.cover} alt={`Cover of ${label}`} size="big" />
      ) : (
        <NoCover title="no cover" />
      )}
      <h2 id={`game-${g.id}`} className={styles.title}>
        {label}
      </h2>
      <div className={styles.meta}>
        <VersionPicker versions={p.versions} current={g.id} onPick={p.onPickVersion} />
        {g.year ? <span>{g.year}</span> : null}
        {g.rating != null && (
          <>
            <span className={styles.rating}>★ {Math.round(g.rating)}</span>
            <span>{(g.votes ?? 0).toLocaleString()} votes</span>
          </>
        )}
        <span>
          {formatBytes(g.size)}
          {g.kind === 'folder' ? ` · ${g.files} files` : ''}
        </span>
        {g.regions.length > 0 && <span>{g.regions.join(', ')}</span>}
      </div>
      {p.device && (
        <div className={styles.select}>
          <Button variant={p.device.selected ? 'primary' : 'default'} onClick={p.device.onToggle}>
            {p.device.selected ? `✓ Selected for ${p.device.name}` : `Select for ${p.device.name}`}
          </Button>
        </div>
      )}
      <TagChipGroup
        genres={g.genres}
        tags={p.tags}
        onRemove={p.onRemoveTag}
        onDecide={p.onDecideTag}
      />
      <TagAdd onAdd={p.onAddTag} />
      <p className={styles.summary}>
        {g.summary || (g.matched ? '' : 'No IGDB match yet. The file name is all we know.')}
      </p>
      {g.igdbName && g.igdbName !== g.title && (
        <KeyValueText>
          IGDB: {g.igdbName}
          {g.confidence ? ` (match ${Math.round(g.confidence * 100)}%)` : ''}
        </KeyValueText>
      )}
      <KeyValueText>{g.name}</KeyValueText>
      <form
        className={styles.rematch}
        onSubmit={(e) => {
          e.preventDefault()
          if (ref.trim()) p.onRematch(ref.trim())
        }}
      >
        <TextInput
          label="Wrong match? The IGDB id, slug or game link"
          hideLabel
          value={ref}
          placeholder="wrong match? paste the IGDB id or game URL"
          onChange={setRef}
        />
        <Button type="submit" disabled={!ref.trim()}>
          Fix match
        </Button>
      </form>
      {p.rematch}
    </article>
  )
}
