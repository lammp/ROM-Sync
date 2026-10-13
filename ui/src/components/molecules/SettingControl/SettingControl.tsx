import { ActionLink } from '../../atoms/ActionLink/ActionLink'
import { Checkbox } from '../../atoms/Checkbox/Checkbox'
import { Select } from '../../atoms/Select/Select'
import { TextInput } from '../../atoms/TextInput/TextInput'
import { PathField } from '../PathField/PathField'
import { helpText, isSize, type Def } from '../../../lib/settings/settings'
import styles from './SettingControl.module.css'

export type SettingDef = Def & { readonly description: string; readonly restart: boolean }

export type SettingControlProps = {
  readonly label: string
  readonly def: SettingDef
  /** Text for a text, number or choice field; a flag for a checkbox. */
  readonly value: string | boolean
  readonly error?: string
  readonly onChange: (value: string | boolean) => void
  /** Offered when a value is stored: put the registry's default back. */
  readonly defaultText?: string
  readonly onDefault?: () => void
  /** A path setting: opens its chooser. Absent where nothing can be chosen. */
  readonly onChoose?: () => void
  /** A path setting names a folder unless it names a file. */
  readonly pathKind?: 'folder' | 'file'
}

/**
 * One registry setting as a control (F11-S34): a checkbox for a flag, a
 * select for a choice, a chooser for a path (F11-S45), otherwise a text
 * field, each with what it takes said under it. The page never hard-codes a
 * setting's kind or range.
 */
export function SettingControl({
  label,
  def,
  value,
  error,
  onChange,
  defaultText,
  onDefault,
  onChoose,
  pathKind = 'folder',
}: SettingControlProps) {
  const help = helpText(def)
  const control =
    def.kind === 'bool' ? (
      <>
        <Checkbox label={label} checked={value === true} onChange={onChange} />
        <span className={styles.help}>{help}</span>
      </>
    ) : def.kind === 'path' ? (
      <PathField
        label={label}
        value={String(value)}
        kind={pathKind}
        help={help}
        error={error}
        onChoose={onChoose}
        onChange={onChange}
      />
    ) : def.choices.length ? (
      <>
        <Select
          label={label}
          value={String(value)}
          options={def.choices.map((c) => ({ value: c, label: c }))}
          onChange={onChange}
        />
        <span className={styles.help}>{help}</span>
      </>
    ) : (
      <TextInput
        label={label}
        value={String(value)}
        onChange={onChange}
        error={error}
        help={help}
        inputMode={
          def.kind === 'int' || def.kind === 'float' ? (isSize(def) ? 'text' : 'numeric') : 'text'
        }
      />
    )
  return (
    <div className={styles.setting}>
      {control}
      {onDefault && (
        <ActionLink onClick={onDefault}>
          {`use the default${defaultText ? ` (${defaultText})` : ''}`}
        </ActionLink>
      )}
    </div>
  )
}
