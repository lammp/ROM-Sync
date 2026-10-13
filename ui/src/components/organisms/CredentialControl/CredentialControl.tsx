import { Pill } from '../../atoms/Pill/Pill'
import { StatusButton, type RunState } from '../../atoms/StatusButton/StatusButton'
import { LockedField } from '../../molecules/LockedField/LockedField'
import {
  SecretField,
  type SecretDraft,
  type SecretState,
} from '../../molecules/SecretField/SecretField'
import styles from './CredentialControl.module.css'

export type { SecretDraft, SecretState }

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
  /** The saved client ID is locked until its edit icon is pressed. */
  readonly clientLocked: boolean
  readonly onUnlockClient: () => void
  /** Puts the saved client ID back and locks it again. */
  readonly onLockClient?: () => void
  readonly secret: SecretState
  readonly draft: SecretDraft
  readonly onDraft: (draft: SecretDraft) => void
  readonly test: {
    readonly result: TestResult | null
    readonly running: boolean
    /** The fields changed since the result: it no longer says anything about them. */
    readonly stale: boolean
  }
  readonly onTest: () => void
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

/** Where Test connection stands: running, its last outcome while it still applies, or not run. */
export function testState(test: CredentialControlProps['test']): RunState {
  if (test.running) return 'running'
  if (!test.result || test.stale) return 'idle'
  return test.result.ok ? 'passed' : 'failed'
}

/**
 * The metadata service's credentials (SETTINGS.md, the IGDB credentials;
 * F11-S52). The client ID locks once saved; the secret is one field that is
 * open while empty and locked once saved, and never reaches the page. Test
 * connection works on what is typed, before it is saved, and shows how it
 * went on the button itself.
 */
export function CredentialControl({
  clientId,
  onClientId,
  clientLocked,
  onUnlockClient,
  onLockClient,
  secret,
  draft,
  onDraft,
  test,
  onTest,
}: CredentialControlProps) {
  const words = test.result ? testWords(test.result) : null
  return (
    <div className={styles.credentials}>
      <LockedField
        label="Twitch client ID"
        value={clientId}
        onChange={onClientId}
        locked={clientLocked}
        onUnlock={onUnlockClient}
        onLock={onLockClient}
        help="From the application registered in the Twitch developer console."
      />
      <SecretField
        label="Client secret"
        stored={secret}
        draft={draft}
        onDraft={onDraft}
        emptyHelp="Covers and details need Twitch credentials; libretro box art does not."
      />
      <div className={styles.row}>
        <StatusButton label="Test connection" state={testState(test)} onClick={onTest} />
        {words && (
          <span role="status">
            <Pill tone={test.stale ? 'neutral' : words.tone}>{words.text}</Pill>
            {test.stale && <span className={styles.stale}> (edited since; test again)</span>}
          </span>
        )}
      </div>
    </div>
  )
}
