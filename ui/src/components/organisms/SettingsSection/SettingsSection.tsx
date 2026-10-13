import type { ReactNode } from 'react'
import { Button } from '../../atoms/Button/Button'
import { Pill, type Tone } from '../../atoms/Pill/Pill'
import styles from './SettingsSection.module.css'

export type SettingsSectionProps = {
  /** The anchor the setup steps and the section nav point at. */
  readonly id: string
  readonly title: string
  /** The section's readiness, in a word; only a problem is loud. */
  readonly status?: { readonly tone: Tone; readonly word: string }
  /** Something in the section is edited and not saved. */
  readonly dirty?: boolean
  readonly saving?: boolean
  /** Absent for a section with nothing to save. */
  readonly onSave?: () => void
  /** Puts back what is stored, dropping the section's edits; offered beside Save. */
  readonly onCancel?: () => void
  /** The section's main actions, drawn prominently at its top, above its settings (F11-S51). */
  readonly actions?: ReactNode
  /**
   * A graphic of the section's state, beside its settings where the section
   * is wide and under its actions where it is not (F11-S53).
   */
  readonly aside?: ReactNode
  readonly children: ReactNode
}

/**
 * One section of the settings page (F11-S34). Saving is explicit and per
 * section, so a job ending elsewhere, or another section's save, never
 * discards what is typed here (SETTINGS.md, principles). Cancel beside Save
 * drops the section's edits and shows what is stored again. What the section
 * does, as against what it sets, sits at its top as its main actions.
 */
export function SettingsSection({
  id,
  title,
  status,
  dirty = false,
  saving = false,
  onSave,
  onCancel,
  actions,
  aside,
  children,
}: SettingsSectionProps) {
  const head = `${id}-title`
  return (
    <section
      id={id}
      className={[styles.section, aside !== undefined && styles.wide].filter(Boolean).join(' ')}
      aria-labelledby={head}
    >
      <div className={styles.grid}>
        <h2 id={head} className={styles.title}>
          {title}
          {dirty && <span className={styles.dirty}>edited</span>}
          {status && <Pill tone={status.tone}>{status.word}</Pill>}
        </h2>
        {actions && (
          <div className={styles.actions} role="group" aria-label={`${title}: actions`}>
            {actions}
          </div>
        )}
        {aside !== undefined && <div className={styles.aside}>{aside}</div>}
        <div className={styles.body}>{children}</div>
        {onSave && (
          <div className={styles.save}>
            {onCancel && (
              <Button small disabled={!dirty || saving} onClick={onCancel}>
                Cancel
              </Button>
            )}
            <Button variant="primary" small disabled={!dirty || saving} onClick={onSave}>
              {saving ? 'Saving…' : `Save ${title.toLowerCase()}`}
            </Button>
          </div>
        )}
      </div>
    </section>
  )
}
