import { Chip } from '../../atoms/Chip/Chip'
import { Select } from '../../atoms/Select/Select'

export type Version = {
  readonly id: number
  readonly sysLabel: string
  readonly year: number | null
  /** Selected for the device in view. */
  readonly selected: boolean
  /** Met only after the release-form strip. */
  readonly loose: boolean
}

export type VersionPickerProps = {
  /** This game and its twins. */
  readonly versions: readonly Version[]
  readonly current: number
  readonly onPick: (id: number) => void
}

/** The game's system, or, when it exists on several, a picker between them ordered by system. */
export function VersionPicker({ versions, current, onPick }: VersionPickerProps) {
  const me = versions.find((v) => v.id === current)
  if (versions.length < 2) return <Chip kind="system">{me?.sysLabel ?? ''}</Chip>
  const options = [...versions]
    .sort((a, b) => a.sysLabel.localeCompare(b.sysLabel))
    .map((v) => ({
      value: String(v.id),
      label: `${v.sysLabel}${v.year ? ` · ${v.year}` : ''}${v.selected ? ' ✓ selected' : ''}${v.loose ? ' (loose)' : ''}`,
    }))
  return (
    <Select
      label={`Version: in the library on ${versions.length} systems`}
      hideLabel
      variant="chip"
      options={options}
      value={String(current)}
      onChange={(v) => Number(v) !== current && onPick(Number(v))}
    />
  )
}
