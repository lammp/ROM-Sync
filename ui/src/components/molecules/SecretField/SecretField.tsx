import { useEffect, useId, useRef, useState } from 'react'
import { IconButton } from '../../atoms/IconButton/IconButton'
import { Icon } from '../../atoms/Icon/Icon'
import styles from './SecretField.module.css'

/** What is known of a saved secret: never the secret itself. */
export type SecretState = {
  readonly present: boolean
  readonly length: number
  readonly savedAt: string | null
  readonly source: string | null
}

/** What the field holds: the saved one, a new one being typed, or the saved one marked for removal. */
export type SecretDraft =
  | { readonly kind: 'keep' }
  | { readonly kind: 'typed'; readonly text: string }
  | { readonly kind: 'remove' }

export type SecretFieldProps = {
  readonly label: string
  readonly stored: SecretState
  readonly draft: SecretDraft
  readonly onDraft: (draft: SecretDraft) => void
  /** Said under an empty field: why it matters. */
  readonly emptyHelp?: string
}

/** "8 Oct 2026", from the saved timestamp. */
export function savedOn(iso: string | null): string {
  if (!iso) return ''
  const d = new Date(iso)
  return Number.isNaN(d.getTime())
    ? iso.slice(0, 10)
    : d.toLocaleDateString('en-GB', {
        day: 'numeric',
        month: 'short',
        year: 'numeric',
        timeZone: 'UTC',
      })
}

/** The dots a saved secret shows as: as many as it has characters, up to a field's width. */
const dots = (n: number) => '•'.repeat(Math.max(8, Math.min(n, 32)))

/**
 * A secret, always shown as one field (F11-S51). Empty, it is open to type
 * in, with an eye to see what is typed. Saved, it is locked and drawn as
 * dots, with an icon to enter a new one and one to remove it: the engine
 * never returns a saved secret, so the eye can only ever show what is being
 * typed now.
 */
export function SecretField({ label, stored, draft, onDraft, emptyHelp }: SecretFieldProps) {
  const id = useId()
  const [shown, setShown] = useState(false)
  const input = useRef<HTMLInputElement>(null)
  const open = draft.kind === 'typed' || (draft.kind === 'keep' && !stored.present)
  const locked = draft.kind === 'keep' && stored.present
  const typing = draft.kind === 'typed'
  const was = useRef(open)
  useEffect(() => {
    if (!was.current && open) input.current?.focus()
    was.current = open
  }, [open])
  const help =
    draft.kind === 'remove'
      ? 'Removed when you save.'
      : locked
        ? `Saved ${savedOn(stored.savedAt)} · ${stored.length} characters${stored.source === 'imported' ? ' · imported from RomCurator' : ''}. A saved secret is never shown again.`
        : stored.present
          ? 'The saved one stays until you save the new one.'
          : emptyHelp
  const short = typing && draft.text.trim() !== '' && draft.text.trim().length < 20
  return (
    <span className={styles.field}>
      <label htmlFor={id} className={styles.label}>
        {label}
      </label>
      <span className={styles.box} data-locked={!open || undefined}>
        <input
          ref={input}
          id={id}
          type={open && shown ? 'text' : 'password'}
          className={styles.input}
          value={typing ? draft.text : locked ? dots(stored.length) : ''}
          readOnly={!open}
          autoComplete="off"
          spellCheck={false}
          aria-describedby={help || short ? `${id}-help` : undefined}
          onChange={(e) => onDraft({ kind: 'typed', text: e.target.value })}
        />
        {open && (
          <IconButton
            label={shown ? `Hide the ${label.toLowerCase()}` : `Show the ${label.toLowerCase()}`}
            aria-pressed={shown}
            onClick={() => setShown((s) => !s)}
          >
            <Icon name={shown ? 'eye-off' : 'eye'} />
          </IconButton>
        )}
        {locked && (
          <>
            <IconButton
              label={`Enter a new ${label.toLowerCase()}`}
              onClick={() => onDraft({ kind: 'typed', text: '' })}
            >
              <Icon name="edit" />
            </IconButton>
            <IconButton
              label={`Remove the saved ${label.toLowerCase()}`}
              onClick={() => onDraft({ kind: 'remove' })}
            >
              <Icon name="remove" />
            </IconButton>
          </>
        )}
        {stored.present && !locked && (
          <IconButton
            label={`Keep the saved ${label.toLowerCase()}`}
            onClick={() => {
              setShown(false)
              onDraft({ kind: 'keep' })
            }}
          >
            <Icon name="undo" />
          </IconButton>
        )}
      </span>
      {(help || short) && (
        <span id={`${id}-help`} className={styles.help}>
          {[help, short && 'That is shorter than a Twitch secret usually is.']
            .filter(Boolean)
            .join(' ')}
        </span>
      )}
    </span>
  )
}
