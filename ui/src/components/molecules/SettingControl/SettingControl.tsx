import { ActionLink } from '../../atoms/ActionLink/ActionLink'
import { Checkbox } from '../../atoms/Checkbox/Checkbox'
import { Select } from '../../atoms/Select/Select'
import { TextInput } from '../../atoms/TextInput/TextInput'
import { LockedField } from '../LockedField/LockedField'
import { PathField } from '../PathField/PathField'
import { SliderField } from '../SliderField/SliderField'
import {
  fromText,
  helpText,
  isSize,
  sizeChoices,
  sizeLabel,
  stepChoices,
  toText,
  type Def,
} from '../../../lib/settings/settings'
import styles from './SettingControl.module.css'

export type SettingDef = Def & { readonly description: string; readonly restart: boolean }

/**
 * How a bounded number is drawn (F11-S51): a scale with its number beside it,
 * a list of its whole steps, or a list of sizes. Anything else is drawn from
 * its kind alone.
 */
export type Presentation =
  | { readonly as: 'slider'; readonly step: number }
  | { readonly as: 'steps' }
  | { readonly as: 'sizes' }

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
  readonly presentation?: Presentation
  /** A typed value that is saved: locked until its edit icon opens it. */
  readonly locked?: boolean
  /** Given for a typed value that locks once saved. */
  readonly onUnlock?: () => void
  /** Puts the saved value back and locks it again, once opened. */
  readonly onLock?: () => void
}

/** The number a field's text stands for, when it stands for one. */
function numberOf(def: Def, text: string): number | null {
  const parsed = fromText({ ...def, minimum: null, maximum: null }, text)
  return parsed.ok && typeof parsed.value === 'number' ? parsed.value : null
}

/**
 * One registry setting as a control (F11-S34, F11-S51): a checkbox for a
 * flag, a list for a choice or a short range, a scale for a bounded number,
 * a chooser for a path (F11-S45), and a field for the rest, locked once
 * saved where the page says so. The registry gives every kind and range;
 * the page says only how a bounded number is best drawn.
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
  presentation,
  locked = false,
  onUnlock,
  onLock,
}: SettingControlProps) {
  const bounded = def.minimum !== null && def.maximum !== null
  const as = bounded ? presentation?.as : undefined
  // a scale or a list shows its own bounds; the words need not say them again
  const help = helpText(as ? { ...def, minimum: null, maximum: null } : def)
  const text = String(value)
  const listed = (values: number[], show: (n: number) => string) => (
    <>
      <Select
        label={label}
        value={text}
        options={values.map((n) => ({ value: toText(def, n), label: show(n) }))}
        onChange={onChange}
      />
      <span className={styles.help}>{help}</span>
    </>
  )
  const control =
    def.kind === 'bool' ? (
      <>
        <Checkbox label={label} checked={value === true} onChange={onChange} />
        <span className={styles.help}>{help}</span>
      </>
    ) : def.kind === 'path' ? (
      <PathField
        label={label}
        value={text}
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
          value={text}
          options={def.choices.map((c) => ({ value: c, label: c }))}
          onChange={onChange}
        />
        <span className={styles.help}>{help}</span>
      </>
    ) : as === 'sizes' && isSize(def) ? (
      listed(sizeChoices(def, numberOf(def, text)), (n) => sizeLabel(def, n))
    ) : as === 'steps' ? (
      listed(stepChoices(def, numberOf(def, text)), (n) => `${n}${def.unit}`)
    ) : as === 'slider' && presentation?.as === 'slider' ? (
      <SliderField
        label={label}
        value={text}
        onChange={onChange}
        min={def.minimum ?? 0}
        max={def.maximum ?? 0}
        step={presentation.step}
        unit={def.unit}
        help={help}
        error={error}
      />
    ) : onUnlock ? (
      <LockedField
        label={label}
        value={text}
        onChange={onChange}
        locked={locked}
        onUnlock={onUnlock}
        onLock={onLock}
        help={help}
        error={error}
        inputMode={def.kind === 'int' || def.kind === 'float' ? 'numeric' : 'text'}
      />
    ) : (
      <TextInput
        label={label}
        value={text}
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
