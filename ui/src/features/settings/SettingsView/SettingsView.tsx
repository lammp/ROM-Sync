'use client'

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from 'react'
import { Button } from '../../../components/atoms/Button/Button'
import { Muted } from '../../../components/atoms/Muted/Muted'
import { DataTable } from '../../../components/molecules/DataTable/DataTable'
import { JobLine, type JobState } from '../../../components/molecules/JobLine/JobLine'
import { LoadError } from '../../../components/molecules/LoadError/LoadError'
import { SettingControl } from '../../../components/molecules/SettingControl/SettingControl'
import { Tabs } from '../../../components/molecules/Tabs/Tabs'
import { TransportList } from '../../../components/molecules/TransportList/TransportList'
import { ConfirmDialog } from '../../../components/organisms/ConfirmDialog/ConfirmDialog'
import { DiagnosticsSummary } from '../../../components/organisms/DiagnosticsSummary/DiagnosticsSummary'
import { FolderBrowser } from '../../../components/organisms/FolderBrowser/FolderBrowser'
import {
  CredentialControl,
  type SecretDraft,
  type TestResult,
} from '../../../components/organisms/CredentialControl/CredentialControl'
import { JobsTable } from '../../../components/organisms/JobsTable/JobsTable'
import { MaintenanceTable } from '../../../components/organisms/MaintenanceTable/MaintenanceTable'
import { SettingsSection } from '../../../components/organisms/SettingsSection/SettingsSection'
import { StorageTable } from '../../../components/organisms/StorageTable/StorageTable'
import { PageLayout } from '../../../components/templates/PageLayout/PageLayout'
import { formatBytes } from '../../../lib/format/format'
import { BROWSER, can, hostOf } from '../../../lib/platform/platform'
import { toText } from '../../../lib/settings/settings'
import { useAttached } from '../../../queries/devices/devices'
import { EngineError, useEngine } from '../../../queries/engine/engine'
import { TERMINAL, useCancelJob, useJob, useJobs } from '../../../queries/job/job'
import {
  useAfterLibraryJob,
  useLibrary,
  useLibraryJob,
  useSystems,
} from '../../../queries/library/library'
import {
  ACTIONS,
  useMaintenanceReports,
  useStorage,
  useRunMaintenance,
  type Action,
} from '../../../queries/maintenance/maintenance'
import {
  useAnnounce,
  useDiagnostics,
  useFolders,
  usePickFolder,
  useReveal,
  useShell,
  useVersion,
} from '../../../queries/meta/meta'
import {
  useSettings,
  useTestCredentials,
  useWriteSettings,
  type Setting,
} from '../../../queries/settings/settings'
import { appStore } from '../../../store/store'
import { LABELS, arrange, toValues, type Draft, type Section } from './model'

const toast = (text: string, bad = false) =>
  appStore.getState().ui.toast(text, bad ? 'bad' : 'info')
const SECRET = 'igdb.client_secret'
const CLIENT = 'igdb.client_id'
const METADATA_JOBS = new Set(['match', 'covers', 'rematch', 'franchise'])

const MAINTENANCE: Readonly<Record<Action, readonly [string, string]>> = {
  compact: ['Compact the database', 'Gives back space the database no longer uses.'],
  'clear-cache': ['Clear the screenshot cache', 'Screenshots fetch again when shown.'],
  'prune-covers': ['Delete unreferenced covers', 'Covers no game points at.'],
  'prune-runs': ['Prune old sync run folders', 'Run folders past the number kept.'],
}

/** Path settings that name a file, and the kinds of file each takes; every other names a folder. */
const FILES: Readonly<Record<string, readonly string[]>> = { 'adb.path': ['exe'] }

/** What a path setting asks its chooser for (F11-S45). */
type Choice = {
  readonly title: string
  readonly kind: 'folder' | 'file'
  readonly current: string
  readonly onPicked: (path: string) => void
}

/** Opens the chooser for a path setting; null where nothing can be chosen. */
const Chooser = createContext<((choice: Choice) => void) | null>(null)

/** The tabs, in first-run order, as SETTINGS.md arranges the sections. */
const TABS = ['library', 'metadata', 'tags', 'transports', 'sync', 'data', 'diagnostics']

/** The tab the address names (`/settings#metadata`), else the first. */
function tabOfHash(): string {
  const named = typeof window === 'undefined' ? '' : window.location.hash.replace(/^#/, '')
  return TABS.includes(named) ? named : 'library'
}

/** A label inside a sentence: "Data folder" reads "data folder"; "ROMs folder" and "ADB executable" keep their capitals. */
const lowerFirst = (label: string) =>
  /^[A-Z][a-z]/.test(label) ? label.charAt(0).toLowerCase() + label.slice(1) : label

/** Where browsing for `current` starts: the folder itself, or the file's folder. */
function startAt(current: string, kind: 'folder' | 'file'): string | null {
  if (!current) return null
  if (kind === 'folder') return current
  const cut = Math.max(current.lastIndexOf('\\'), current.lastIndexOf('/'))
  return cut > 0 ? current.slice(0, cut + (current[cut - 1] === ':' ? 1 : 0)) : null
}

/** A job a section started: its line while it runs, its sentence when it ends. */
function useSectionJob(done: () => void) {
  const [id, setId] = useState<string | null>(null)
  const job = useJob(id).data
  const announce = useAnnounce()
  const ended = useRef<string | null>(null)
  useEffect(() => {
    if (!job || !TERMINAL.has(job.state) || ended.current === job.id) return
    ended.current = job.id
    if (job.state === 'failed') announce(job, job.error_message ?? `${job.kind} failed`, true)
    else
      announce(
        job,
        `${job.kind} ${job.state}${
          job.result
            ? `: ${Object.entries(job.result)
                .map(([k, v]) => `${k} ${v}`)
                .join(', ')}`
            : ''
        }`,
      )
    done()
  }, [job, done, announce])
  const line = job ? (
    <JobLine
      state={job.state as JobState}
      progress={job.progress}
      result={job.result}
      error={job.error_message}
    />
  ) : null
  const running = job !== undefined && !TERMINAL.has(job.state)
  return { start: setId, line, running }
}

type FieldsProps = {
  readonly section: Section
  readonly byKey: ReadonlyMap<string, Setting>
  readonly drafts: Readonly<Record<string, Draft>>
  readonly errors: Readonly<Record<string, string>>
  readonly onDraft: (key: string, draft: Draft) => void
  readonly skip?: ReadonlySet<string>
}

/** A section's registry fields, each showing its draft over the stored value. */
function Fields({ section, byKey, drafts, errors, onDraft, skip }: FieldsProps) {
  const choose = useContext(Chooser)
  return (
    <>
      {section.keys
        .filter((k) => !skip?.has(k))
        .map((key) => {
          const s = byKey.get(key)
          if (!s) return null
          const draft = drafts[key]
          const value =
            s.kind === 'bool'
              ? typeof draft === 'boolean'
                ? draft
                : draft === null
                  ? s.default === true
                  : s.value === true
              : typeof draft === 'string'
                ? draft
                : toText(s, draft === null ? s.default : s.value)
          return (
            <SettingControl
              key={key}
              label={LABELS[key] ?? key}
              def={s}
              value={value}
              error={errors[key]}
              onChange={(v) => onDraft(key, v)}
              defaultText={s.kind === 'bool' ? undefined : toText(s, s.default) || 'none'}
              onDefault={s.stored && draft !== null ? () => onDraft(key, null) : undefined}
              pathKind={key in FILES ? 'file' : 'folder'}
              onChoose={
                s.kind === 'path' && choose
                  ? () =>
                      choose({
                        title: `Choose the ${lowerFirst(LABELS[key] ?? key)}`,
                        kind: key in FILES ? 'file' : 'folder',
                        current: String(value),
                        onPicked: (path) => onDraft(key, path),
                      })
                  : undefined
              }
            />
          )
        })}
    </>
  )
}

/** One section's edits, kept apart from every other section's and from the stored values. */
function useDrafts(title: string) {
  const [drafts, setDrafts] = useState<Record<string, Draft>>({})
  const [errors, setErrors] = useState<Record<string, string>>({})
  const write = useWriteSettings()
  const onDraft = (key: string, draft: Draft) => {
    setDrafts((d) => ({ ...d, [key]: draft }))
    setErrors((e) => {
      const rest = { ...e }
      delete rest[key]
      return rest
    })
  }
  const save = (byKey: ReadonlyMap<string, Setting>, extra: Record<string, string | null> = {}) => {
    const defs = Object.fromEntries([...byKey].filter(([k]) => k in drafts))
    const out = toValues(drafts, defs)
    if ('errors' in out) {
      setErrors(out.errors)
      return
    }
    write.mutate(
      { ...out.values, ...extra },
      {
        onSuccess: () => {
          setDrafts({})
          setErrors({})
          toast(`${title} saved`)
        },
        onError: (e) => {
          if (e instanceof EngineError && e.field) setErrors({ [e.field]: e.message })
          else toast(e.message, true)
        },
      },
    )
  }
  const reset = () => {
    setDrafts({})
    setErrors({})
  }
  return { drafts, errors, onDraft, save, saving: write.isPending, reset }
}

type SectionProps = {
  readonly section: Section
  readonly byKey: ReadonlyMap<string, Setting>
  /** Told whenever the section's edits start or stop being unsaved, for its tab's mark. */
  readonly onDirty?: (edited: boolean) => void
  readonly status?: { readonly tone: 'ok' | 'warn' | 'bad'; readonly word: string }
  /** What the section carries besides its fields; given the section's own draft setter. */
  readonly children?: ReactNode | ((onDraft: (key: string, draft: Draft) => void) => ReactNode)
}

const carried = (
  children: SectionProps['children'],
  onDraft: (key: string, draft: Draft) => void,
) => (typeof children === 'function' ? children(onDraft) : children)

/** A section of plain registry fields and whatever it carries besides. */
function PlainSection({ section, byKey, status, onDirty, children }: SectionProps) {
  const d = useDrafts(section.title)
  const edited = Object.keys(d.drafts).length > 0
  useEffect(() => onDirty?.(edited), [edited, onDirty])
  return (
    <SettingsSection
      id={section.id}
      title={section.title}
      status={status}
      dirty={Object.keys(d.drafts).length > 0}
      saving={d.saving}
      onSave={section.keys.length ? () => d.save(byKey) : undefined}
      onCancel={section.keys.length ? d.reset : undefined}
    >
      <Fields
        section={section}
        byKey={byKey}
        drafts={d.drafts}
        errors={d.errors}
        onDraft={d.onDraft}
      />
      {carried(children, d.onDraft)}
    </SettingsSection>
  )
}

/** Metadata: the credentials as their own control, the rest from the registry, and the passes. */
function MetadataSection({ section, byKey, status, onDirty, children }: SectionProps) {
  const d = useDrafts(section.title)
  const [secret, setSecret] = useState<SecretDraft>({ kind: 'keep' })
  const test = useTestCredentials()
  const [tested, setTested] = useState<{ result: TestResult; against: string } | null>(null)
  const stored = byKey.get(SECRET)?.secret_state
  const clientId =
    typeof d.drafts[CLIENT] === 'string'
      ? (d.drafts[CLIENT] as string)
      : String(byKey.get(CLIENT)?.value ?? '')
  const typed = secret.kind === 'typed' ? secret.text : null
  const signature = `${clientId}\u0000${typed ?? ''}\u0000${secret.kind}`
  const dirty =
    Object.keys(d.drafts).length > 0 ||
    secret.kind === 'remove' ||
    (secret.kind === 'typed' && secret.text.trim() !== '')
  useEffect(() => onDirty?.(dirty), [dirty, onDirty])
  return (
    <SettingsSection
      id={section.id}
      title={section.title}
      status={status}
      dirty={dirty}
      saving={d.saving}
      onSave={() => {
        const extra: Record<string, string | null> =
          secret.kind === 'remove'
            ? { [SECRET]: null }
            : secret.kind === 'typed' && secret.text.trim()
              ? { [SECRET]: secret.text.trim() }
              : {}
        d.save(byKey, extra)
        setSecret({ kind: 'keep' })
      }}
      onCancel={() => {
        d.reset()
        setSecret({ kind: 'keep' })
        setTested(null)
      }}
    >
      <CredentialControl
        clientId={clientId}
        onClientId={(v) => d.onDraft(CLIENT, v)}
        secret={{
          present: stored?.present ?? false,
          length: stored?.length ?? 0,
          savedAt: stored?.saved_at ?? null,
          source: stored?.source ?? null,
        }}
        draft={secret}
        onDraft={setSecret}
        test={{
          result: tested?.result ?? null,
          running: test.isPending,
          stale: tested !== null && tested.against !== signature,
        }}
        onTest={() =>
          test.mutate(
            {
              client_id: CLIENT in d.drafts ? clientId : null,
              client_secret: typed?.trim() ? typed.trim() : null,
            },
            {
              onSuccess: (r) =>
                setTested({
                  result: { ok: r.ok, failedAt: r.failed_at, stages: r.stages },
                  against: signature,
                }),
              onError: (e) => toast(e.message, true),
            },
          )
        }
      />
      <Fields
        section={section}
        byKey={byKey}
        drafts={d.drafts}
        errors={d.errors}
        onDraft={d.onDraft}
        skip={new Set([CLIENT, SECRET])}
      />
      {carried(children, d.onDraft)}
    </SettingsSection>
  )
}

/**
 * The settings page (F11-S34), built to SETTINGS.md: setup first while it is
 * incomplete, then the sections in first-run order, each saving on its own,
 * every field drawn from the engine's registry.
 */
export function SettingsView() {
  const settings = useSettings()
  const systems = useSystems()
  const library = useLibrary()
  const jobs = useJobs()
  const cancelJob = useCancelJob()
  const version = useVersion().data
  const diagnostics = useDiagnostics()
  const { baseUrl } = useEngine()
  const attached = useAttached()
  const shell = useShell().data ?? BROWSER
  const pick = usePickFolder()
  const reveal = useReveal()
  const reports = useMaintenanceReports()
  const storage = useStorage()
  const runMaintenance = useRunMaintenance()
  // the first tab until the page is in the browser, then the one the address names
  const [tab, setTab] = useState('library')
  const [dirty, setDirty] = useState<ReadonlySet<string>>(new Set())
  // a notification that points at a tab, followed while this page is open
  useEffect(() => {
    const follow = () => setTab(tabOfHash())
    queueMicrotask(follow)
    window.addEventListener('hashchange', follow)
    return () => window.removeEventListener('hashchange', follow)
  }, [])
  const selectTab = (id: string) => {
    setTab(id)
    try {
      window.history.replaceState(null, '', `#${id}`)
    } catch {
      // no history to write: the tab is still shown
    }
  }
  const dirtyIn = useCallback(
    (id: string) => (edited: boolean) =>
      setDirty((now) => {
        if (now.has(id) === edited) return now
        const next = new Set(now)
        if (edited) next.add(id)
        else next.delete(id)
        return next
      }),
    [],
  )
  const [browsing, setBrowsing] = useState<(Choice & { readonly path: string | null }) | null>(null)
  const folders = useFolders(
    browsing?.path ?? null,
    browsing?.kind === 'file' ? (FILES['adb.path'] ?? []) : [],
    browsing !== null,
  )
  const [ask, setAsk] = useState<null | {
    title: string
    body: string
    confirm: string
    danger?: boolean
    run: () => void
  }>(null)

  const refreshLibrary = useAfterLibraryJob()
  const scanJob = useSectionJob(refreshLibrary)
  const metaJob = useSectionJob(refreshLibrary)
  const tagJob = useSectionJob(refreshLibrary)
  const scan = useLibraryJob('/api/v1/library/scan')
  const match = useLibraryJob('/api/v1/library/match')
  const covers = useLibraryJob('/api/v1/library/covers')
  const franchises = useLibraryJob('/api/v1/library/franchises')

  if (settings.isError)
    return (
      <PageLayout heading="Settings">
        <LoadError
          what="the settings"
          message={settings.error.message}
          retrying={settings.isFetching}
          onRetry={() => void settings.refetch()}
        />
      </PageLayout>
    )
  if (!settings.data) return <Muted>loading…</Muted>

  const byKey = new Map(settings.data.map((s) => [s.key, s]))
  const sections = arrange(settings.data.map((s) => s.key))
  const section = (id: string) => sections.find((s) => s.id === id) as Section
  const storeRoot = String(byKey.get('store.root')?.value ?? '')
  const sys = systems.data ?? []
  const games = library.data?.games ?? []
  const credentials =
    Boolean(byKey.get(CLIENT)?.value) && Boolean(byKey.get(SECRET)?.secret_state?.present)
  const pending = games.filter((g) => g.state === 'pending').length
  const coverless = games.filter((g) => g.matched && !g.coverUrl).length
  const metadataBusy = (jobs.data ?? []).some(
    (j) => METADATA_JOBS.has(j.kind) && !TERMINAL.has(j.state),
  )

  const startJob = (
    m: {
      mutate: (
        v: undefined,
        cb: { onSuccess: (j: { id: string }) => void; onError: (e: Error) => void },
      ) => void
    },
    into: (id: string) => void,
  ) =>
    m.mutate(undefined, {
      onSuccess: (j) => {
        into(j.id)
        void jobs.refetch()
      },
      onError: (e) => toast(e.message, true),
    })

  /**
   * In the desktop window a folder is chosen in the window's own dialog; a file,
   * and anything in a browser, in this page's folder browser (F11-S45).
   */
  const browse = (choice: Choice) =>
    setBrowsing({ ...choice, path: startAt(choice.current, choice.kind) })
  const choose =
    can(shell, 'pick_folder') || can(shell, 'browse_folders')
      ? (choice: Choice) => {
          if (choice.kind === 'folder' && shell.kind === 'desktop' && can(shell, 'pick_folder'))
            pick.mutate(choice.title, {
              onSuccess: (path) => {
                if (path) choice.onPicked(path)
              },
              // a dialog the window cannot open still leaves a way to choose
              onError: () => (can(shell, 'browse_folders') ? browse(choice) : undefined),
            })
          else browse(choice)
        }
      : null

  const rescan = () => {
    const run = () => startJob(scan, scanJob.start)
    if (games.length)
      setAsk({
        title: 'Rescan the ROMs folder',
        body: `Read ${storeRoot || 'the ROMs folder'} again and replace the library's record of ${games.length.toLocaleString()} games with what is there now. Matches, tags and selections are kept for games still present.`,
        confirm: 'Rescan',
        run,
      })
    else run()
  }

  return (
    <Chooser.Provider value={choose}>
      <PageLayout heading="Settings">
        <Tabs
          label="Settings groups"
          selected={tab}
          onSelect={selectTab}
          tabs={[
            {
              id: 'library',
              label: section('library').title,
              dirty: dirty.has('library'),
              panel: (
                <PlainSection
                  section={section('library')}
                  byKey={byKey}
                  onDirty={dirtyIn('library')}
                  status={
                    !storeRoot
                      ? { tone: 'bad', word: 'no ROMs folder chosen' }
                      : sys.length
                        ? {
                            tone: 'ok',
                            word: `${sys.length} systems · ${games.length.toLocaleString()} games`,
                          }
                        : { tone: 'warn', word: 'no systems found here' }
                  }
                >
                  {() => (
                    <>
                      <p>
                        {can(shell, 'reveal') && storeRoot && (
                          <Button small onClick={() => reveal.mutate({ root: 'store' })}>
                            Reveal
                          </Button>
                        )}{' '}
                        <Button small disabled={!storeRoot || scanJob.running} onClick={rescan}>
                          Rescan ROMs folder
                        </Button>
                      </p>
                      {scanJob.line}
                      <DataTable
                        caption="Systems in the ROMs folder"
                        columns={[
                          {
                            key: 'system',
                            label: 'System',
                            cell: (s: (typeof sys)[number]) => `${s.label} (${s.key})`,
                          },
                          {
                            key: 'games',
                            label: 'Games',
                            numeric: true,
                            cell: (s: (typeof sys)[number]) => s.games.toLocaleString(),
                          },
                          {
                            key: 'bytes',
                            label: 'Size',
                            numeric: true,
                            cell: (s: (typeof sys)[number]) => formatBytes(s.bytes),
                          },
                        ]}
                        rows={sys}
                        rowKey={(s) => s.key}
                        empty="No systems found. Check the ROMs folder, then rescan."
                      />
                    </>
                  )}
                </PlainSection>
              ),
            },
            {
              id: 'metadata',
              label: section('metadata').title,
              dirty: dirty.has('metadata'),
              panel: (
                <MetadataSection
                  section={section('metadata')}
                  byKey={byKey}
                  onDirty={dirtyIn('metadata')}
                  status={
                    credentials
                      ? { tone: 'ok', word: 'credentials set' }
                      : { tone: 'warn', word: 'no credentials' }
                  }
                >
                  <p>
                    <Button
                      small
                      disabled={!pending || metadataBusy || !credentials}
                      title={credentials ? undefined : 'Add credentials first'}
                      onClick={() =>
                        setAsk({
                          title: 'Match new games',
                          body: `Look up ${pending.toLocaleString()} unmatched games on IGDB, at up to ${String(byKey.get('igdb.requests_per_second')?.value ?? 4)} requests a second.`,
                          confirm: 'Match',
                          run: () => startJob(match, metaJob.start),
                        })
                      }
                    >
                      Match new ({pending.toLocaleString()})
                    </Button>{' '}
                    <Button
                      small
                      disabled={!coverless || metadataBusy}
                      onClick={() => startJob(covers, metaJob.start)}
                    >
                      Fill missing covers ({coverless.toLocaleString()})
                    </Button>
                  </p>
                  {metaJob.line}
                </MetadataSection>
              ),
            },
            {
              id: 'tags',
              label: section('tags').title,
              dirty: dirty.has('tags'),
              panel: (
                <PlainSection section={section('tags')} byKey={byKey} onDirty={dirtyIn('tags')}>
                  <p>
                    <Button
                      small
                      disabled={metadataBusy || tagJob.running}
                      onClick={() => startJob(franchises, tagJob.start)}
                    >
                      Propose franchise tags
                    </Button>{' '}
                    <Muted>
                      Proposals wait for a decision in each game&apos;s details; a decision is never
                      overwritten.
                    </Muted>
                  </p>
                  {tagJob.line}
                </PlainSection>
              ),
            },
            {
              id: 'transports',
              label: section('transports').title,
              dirty: dirty.has('transports'),
              panel: (
                <PlainSection
                  section={section('transports')}
                  byKey={byKey}
                  onDirty={dirtyIn('transports')}
                >
                  <TransportList transports={attached.data?.transports ?? []} />
                </PlainSection>
              ),
            },
            {
              id: 'sync',
              label: section('sync').title,
              dirty: dirty.has('sync'),
              panel: (
                <PlainSection section={section('sync')} byKey={byKey} onDirty={dirtyIn('sync')} />
              ),
            },
            {
              id: 'data',
              label: section('data').title,
              dirty: dirty.has('data'),
              panel: (
                <PlainSection section={section('data')} byKey={byKey} onDirty={dirtyIn('data')}>
                  {can(shell, 'reveal') && (
                    <p>
                      <Button small onClick={() => reveal.mutate({ root: 'data' })}>
                        Reveal the data folder
                      </Button>
                    </p>
                  )}
                  {storage.isError ? (
                    <LoadError
                      what="the storage breakdown"
                      message={storage.error.message}
                      retrying={storage.isFetching}
                      onRetry={() => void storage.refetch()}
                    />
                  ) : (
                    <StorageTable parts={storage.data?.components ?? []} />
                  )}
                  <MaintenanceTable
                    busy={runMaintenance.isPending}
                    rows={ACTIONS.map((action, i) => {
                      const r = reports[i]?.data
                      const [label, what] = MAINTENANCE[action]
                      return {
                        action,
                        label,
                        what,
                        count: r ? r.count : null,
                        bytes: r?.bytes ?? 0,
                        onRun: () =>
                          r &&
                          setAsk({
                            title: label,
                            body: `${label}: ${r.count.toLocaleString()} item${r.count === 1 ? '' : 's'}, ${formatBytes(r.bytes)}.`,
                            confirm: 'Run',
                            danger: action !== 'compact',
                            run: () =>
                              runMaintenance.mutate(
                                { action, expected: r.count },
                                {
                                  onSuccess: () => toast(`${label}: started`),
                                  onError: (e) => toast(e.message, true),
                                },
                              ),
                          }),
                      }
                    })}
                  />
                </PlainSection>
              ),
            },
            {
              id: 'diagnostics',
              label: section('diagnostics').title,
              dirty: dirty.has('diagnostics'),
              panel: (
                <PlainSection
                  section={section('diagnostics')}
                  byKey={byKey}
                  onDirty={dirtyIn('diagnostics')}
                >
                  {diagnostics.isError ? (
                    <LoadError
                      what="the diagnostics"
                      message={diagnostics.error.message}
                      retrying={diagnostics.isFetching}
                      onRetry={() => void diagnostics.refetch()}
                    />
                  ) : (
                    <DiagnosticsSummary
                      version={
                        version
                          ? `${version.application} ${version.version} · API ${version.api}`
                          : ''
                      }
                      host={hostOf(shell)}
                      address={diagnostics.data?.address ?? ''}
                      dataFolder={diagnostics.data?.data_folder ?? ''}
                      logFolder={diagnostics.data?.log_folder ?? ''}
                      lastSync={
                        diagnostics.data?.last_sync
                          ? {
                              device: diagnostics.data.last_sync.device,
                              started: diagnostics.data.last_sync.run.started,
                              state: diagnostics.data.last_sync.run.state,
                              counts: diagnostics.data.last_sync.run.counts ?? {},
                              bytes: diagnostics.data.last_sync.run.bytes_moved ?? null,
                            }
                          : null
                      }
                      errors={diagnostics.data?.recent_errors ?? []}
                      bundleHref={`${baseUrl}/api/v1/diagnostics/bundle`}
                    />
                  )}
                  <JobsTable
                    jobs={(jobs.data ?? []).map((j) => ({
                      id: j.id,
                      kind: j.kind,
                      started: j.started,
                      state: j.state,
                      progress: j.progress,
                      error: j.error_message,
                    }))}
                    onCancel={(id) =>
                      cancelJob.mutate(id, { onSuccess: () => void jobs.refetch() })
                    }
                  />
                </PlainSection>
              ),
            },
          ]}
        />

        {ask && (
          <ConfirmDialog
            title={ask.title}
            confirm={ask.confirm}
            danger={ask.danger}
            onCancel={() => setAsk(null)}
            onConfirm={() => {
              const run = ask.run
              setAsk(null)
              run()
            }}
          >
            {ask.body}
          </ConfirmDialog>
        )}
        {browsing && (
          <FolderBrowser
            title={browsing.title}
            kind={browsing.kind}
            listing={folders.data}
            loading={folders.isFetching}
            error={folders.error?.message}
            onOpen={(path) => setBrowsing({ ...browsing, path })}
            onChoose={(path) => {
              browsing.onPicked(path)
              setBrowsing(null)
            }}
            onCancel={() => setBrowsing(null)}
          />
        )}
      </PageLayout>
    </Chooser.Provider>
  )
}
