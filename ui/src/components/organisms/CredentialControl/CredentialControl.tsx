import { Button } from '../../atoms/Button/Button'
import { Muted } from '../../atoms/Muted/Muted'
import { PasswordInput } from '../../atoms/PasswordInput/PasswordInput'
import { Pill } from '../../atoms/Pill/Pill'
import { TextInput } from '../../atoms/TextInput/TextInput'
import styles from './CredentialControl.module.css'

export type SecretState = {
  readonly present: boolean
  readonly length: number
  readonly savedAt: string | null
  readonly source: string | null
}

/** What the secret field holds: untouched, being typed, or marked for removal. */
export type SecretDraft =
  | { readonly kind: 'keep' }
  | { readonly kind: 'typed'; readonly text: string }
  | { readonly kind: 'remove' }

export type TestStage = {
  readonly name: string
  readonly outcome: string
  readonly message: string | null
}
export type TestResult = {
  readonly ok: boolean
  readonly failedAt: string | null
  readonly stages: readonly TestStage[]
}

export type CredentialControlProps = {
  readonly clientId: string
  readonly onClientId: (value: string) => void
  readonly secret: SecretState
  readonly draft: SecretDraft
  readonly onDraft: (draft: SecretDraft) => void
  readonly test: {
    readonly result: TestResult | null
    readonly running: boolean
    readonly stale: boolean
  }
  readonly onTest: () => void
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

/** A test's outcome in words: what passed, or which stage failed and why. */
export function testWords(r: TestResult): { readonly tone: 'ok' | 'bad'; readonly text: string } {
  if (r.ok) return { tone: 'ok', text: `connected: ${r.stages.map((s) => s.name).join(', ')} ok` }
  const failed = r.stages.find((s) => s.name === r.failedAt)
  return {
    tone: 'bad',
    text: `${r.failedAt ?? 'test'} failed${failed?.message ? `: ${failed.message}` : ''}`,
  }
}

/**
 * The metadata service's credentials (SETTINGS.md, the IGDB credentials).
 * The secret never reaches the page: a stored one is described by its length
 * and save date, and the input exists only once Replace or Add is pressed.
 * Test connection works on what is typed, before it is saved.
 */
export function CredentialControl({
  clientId,
  onClientId,
  secret,
  draft,
  onDraft,
  test,
  onTest,
}: CredentialControlProps) {
  const typing = draft.kind === 'typed'
  const removing = draft.kind === 'remove'
  return (
    <div className={styles.credentials}>
      <TextInput label="Twitch client ID" value={clientId} onChange={onClientId} />
      <div className={styles.secret}>
        <span className={styles.label}>Client secret</span>
        {typing ? (
          <>
            <PasswordInput
              label="New client secret"
              value={draft.text}
              onChange={(text) => onDraft({ kind: 'typed', text })}
              stored={secret.present}
            />
            {draft.text && draft.text.trim().length < 20 && (
              <Muted>That is shorter than a Twitch secret usually is.</Muted>
            )}
            <Button small onClick={() => onDraft({ kind: 'keep' })}>
              Keep the saved one
            </Button>
          </>
        ) : removing ? (
          <>
            <Muted>Will be removed when this section is saved.</Muted>
            <Button small onClick={() => onDraft({ kind: 'keep' })}>
              Keep it
            </Button>
          </>
        ) : secret.present ? (
          <>
            <span>
              Saved {savedOn(secret.savedAt)} · {secret.length} characters · not shown again
              {secret.source === 'imported' && <Muted> · imported from RomCurator</Muted>}
            </span>
            <span className={styles.row}>
              <Button small onClick={() => onDraft({ kind: 'typed', text: '' })}>
                Replace
              </Button>
              <Button small variant="danger" onClick={() => onDraft({ kind: 'remove' })}>
                Remove
              </Button>
            </span>
          </>
        ) : (
          <>
            <Muted>
              Not set. Covers and details need Twitch credentials; libretro box art does not.
            </Muted>
            <Button small onClick={() => onDraft({ kind: 'typed', text: '' })}>
              Add credentials
            </Button>
          </>
        )}
      </div>
      <div className={styles.row}>
        <Button small disabled={test.running} onClick={onTest}>
          {test.running ? 'Testing…' : 'Test connection'}
        </Button>
        {test.result &&
          (() => {
            const w = testWords(test.result)
            return (
              <span role="status">
                <Pill tone={test.stale ? 'neutral' : w.tone}>{w.text}</Pill>
                {test.stale && <Muted> (edited since; test again)</Muted>}
              </span>
            )
          })()}
      </div>
    </div>
  )
}
