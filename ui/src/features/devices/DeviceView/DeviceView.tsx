'use client'

import { useRouter } from 'next/navigation'
import { useEffect, useMemo, useRef, useState } from 'react'
import { Bar } from '../../../components/atoms/Bar/Bar'
import { Button } from '../../../components/atoms/Button/Button'
import { Muted } from '../../../components/atoms/Muted/Muted'
import { Pill } from '../../../components/atoms/Pill/Pill'
import { JobLine, type JobState } from '../../../components/molecules/JobLine/JobLine'
import { LoadError } from '../../../components/molecules/LoadError/LoadError'
import { PlanDetailList } from '../../../components/molecules/PlanDetailList/PlanDetailList'
import { PlanLine } from '../../../components/molecules/PlanLine/PlanLine'
import { SyncControl, type SyncState } from '../../../components/molecules/SyncControl/SyncControl'
import { ConfirmDialog } from '../../../components/organisms/ConfirmDialog/ConfirmDialog'
import { seenAt, TRANSPORT } from '../../../components/organisms/DeviceCard/DeviceCard'
import { PromptDialog } from '../../../components/organisms/PromptDialog/PromptDialog'
import { RunHistory } from '../../../components/organisms/RunHistory/RunHistory'
import { SyncConfirm } from '../../../components/organisms/SyncConfirm/SyncConfirm'
import { SystemsTable } from '../../../components/organisms/SystemsTable/SystemsTable'
import { PageLayout } from '../../../components/templates/PageLayout/PageLayout'
import { formatBytes } from '../../../lib/format/format'
import {
  attachedFor,
  useAttached,
  useCapacity,
  useInventory,
  usePlan,
  useProfiles,
  useRefreshCapacity,
  useRename,
  useRuns,
  useScan,
  useSelection,
  useSetMode,
  useWriteMarker,
} from '../../../queries/devices/devices'
import { EngineError } from '../../../queries/engine/engine'
import { TERMINAL, useJob } from '../../../queries/job/job'
import { useAnnounce } from '../../../queries/meta/meta'
import { useLibrary, useSystems } from '../../../queries/library/library'
import { useAfterDeviceJob, useCancelSync, useStartSync } from '../../../queries/sync/sync'
import { useSysReport } from '../../../queries/sysfiles/sysfiles'
import { appStore, useAppStore } from '../../../store/store'
import styles from './DeviceView.module.css'
import { readinessLine, startOf, systemRows, workIn, type ReadinessLine } from './model'

type Ask = 'rename' | 'marker' | 'sync' | null

function SysfilesLine({ connected, line }: { connected: boolean; line: ReadinessLine | null }) {
  if (!connected) return <Muted>Plug the device in to read its system files.</Muted>
  if (!line) return <Muted>loading…</Muted>
  if (line.kind === 'missing')
    return (
      <p className={styles.pills}>
        {line.items.map((i) => (
          <Pill key={i} tone="bad">
            {i}
          </Pill>
        ))}
      </p>
    )
  return (
    <Muted>
      {line.kind === 'unread'
        ? 'Not read yet: open System files and press Refresh from device.'
        : 'Every system on the device has what its emulator needs.'}
    </Muted>
  )
}

const toast = (text: string, bad = false) =>
  appStore.getState().ui.toast(text, bad ? 'bad' : 'info')

/**
 * One device's page (F11-S32), at `/devices?id=`: what it holds by system and
 * each system's mode, what a sync would do, its history, and its actions.
 * Whether it is plugged in is read from the device query, which asks again
 * at the probe interval and stops when the page goes.
 */
export function DeviceView({ id }: { id: string }) {
  const router = useRouter()
  const profiles = useProfiles()
  const profile = profiles.data?.find((p) => p.id === id) ?? null
  const attached = useAttached()
  const device = attachedFor(attached.data?.devices ?? [], id)
  const ref = device?.ref ?? null
  const connected = device !== null
  const systems = useSystems().data ?? []
  const games = useLibrary().data?.games
  const selection = useSelection(id).data ?? null
  const inventory = useInventory(id).data
  const runs = useRuns(id).data ?? []
  const plan = usePlan(ref)
  const sysQuery = useSysReport(ref)
  const sysfiles = sysQuery.data
  const live = useCapacity(ref).data
  const refresh = useRefreshCapacity(ref)
  const setMode = useSetMode(id)
  const rename = useRename(id)
  const scan = useScan(ref ?? '')
  const marker = useWriteMarker(ref ?? '')
  const start = useStartSync(ref ?? '')
  const cancel = useCancelSync(ref ?? '')
  const afterJob = useAfterDeviceJob(id, ref)
  const announce = useAnnounce()
  const running = useAppStore((s) => s.sync.running)
  const syncing = running !== null && running.device === id
  const [ask, setAsk] = useState<Ask>(null)
  const [jobId, setJobId] = useState<string | null>(null)
  const job = useJob(jobId).data

  // A device job (scan, marker) that has ended reads the device's figures again.
  const ended = useRef<string | null>(null)
  useEffect(() => {
    if (!job || !TERMINAL.has(job.state) || ended.current === job.id) return
    ended.current = job.id
    if (job.state === 'failed') announce(job, job.error_message ?? 'The device job failed', true)
    else if (job.kind === 'device' && job.result?.games !== undefined)
      announce(
        job,
        `Read ${job.result.games.toLocaleString()} game${job.result.games === 1 ? '' : 's'} from the device`,
      )
    else if (job.result?.written) announce(job, 'ROM-Sync.json written')
    afterJob()
  }, [job, afterJob, announce])

  const systemOf = useMemo(() => new Map((games ?? []).map((g) => [g.id, g.system])), [games])
  const held = inventory ?? []
  const rows = systemRows(systems, held, selection, systemOf)
  const busy = jobId !== null && job !== undefined && !TERMINAL.has(job.state)

  if (profiles.isSuccess && !profile)
    return (
      <PageLayout heading="Device not found">
        <p>
          No device profile <code>{id}</code>.{' '}
          <Button small onClick={() => router.push('/devices')}>
            All devices
          </Button>
        </p>
      </PageLayout>
    )
  if (profiles.isError)
    return (
      <PageLayout heading="Device">
        <LoadError
          what="the device profiles"
          message={profiles.error.message}
          retrying={profiles.isFetching}
          onRetry={() => void profiles.refetch()}
        />
      </PageLayout>
    )
  if (!profile) return <Muted>loading…</Muted>

  const space =
    live ??
    (profile.capacity != null && profile.free != null
      ? { total: profile.capacity, free: profile.free }
      : null)
  const where = [
    TRANSPORT[device?.kind ?? profile.kind] ?? profile.kind,
    `ROMs folder: ${device?.roms_root ?? profile.roms_root}`,
    connected
      ? space
        ? `${formatBytes(space.free)} free of ${formatBytes(space.total)}`
        : 'capacity unknown'
      : `last seen ${seenAt(profile.last_seen)}`,
  ].join(' · ')

  const p = plan.data
  const syncState: SyncState = syncing
    ? { kind: 'running', reading: running.reading }
    : !connected
      ? { kind: 'disabled', reason: 'Plug the device in to sync' }
      : busy
        ? { kind: 'disabled', reason: 'Another job is using the device' }
        : {
            kind: 'idle',
            onSync: () => {
              if (!p) return
              if (!workIn(p)) toast('Nothing to do: the device already matches your selection')
              else if (p.bytes.fits === false)
                toast(
                  `Does not fit: the selection needs ${formatBytes(p.bytes.peak - (p.bytes.free ?? 0))} more than the device has`,
                  true,
                )
              else setAsk('sync')
            },
          }

  const runJob = (m: typeof scan) =>
    m.mutate(undefined, {
      onSuccess: (j) => setJobId(j.id),
      onError: (e) => toast(e.message, true),
    })

  return (
    <PageLayout
      heading={
        <>
          {profile.name}{' '}
          <Pill tone={connected ? 'ok' : 'warn'}>{connected ? 'connected' : 'not plugged in'}</Pill>
        </>
      }
      actions={
        <>
          <Button small onClick={() => setAsk('rename')}>
            Rename
          </Button>
          <Button
            small
            onClick={() => {
              appStore.getState().selection.choose(id)
              router.push('/')
            }}
          >
            Select games in Library
          </Button>
          <SyncControl state={syncState} />
          {syncing && (
            <Button small variant="danger" onClick={() => cancel.mutate()}>
              Cancel sync
            </Button>
          )}
          <Button small disabled={!connected || busy || syncing} onClick={() => runJob(scan)}>
            Scan device
          </Button>
          <Button
            small
            disabled={!connected || busy || syncing}
            title="Rewrite ROM-Sync.json on the device"
            onClick={() => setAsk('marker')}
          >
            Write ROM-Sync.json
          </Button>
        </>
      }
    >
      <Muted>{where}</Muted>
      {connected && space && (
        <Bar value={1 - space.free / space.total} label="Space used" valueText={where} />
      )}
      {job && (
        <JobLine
          state={job.state as JobState}
          progress={job.progress}
          result={job.result}
          error={job.error_message}
        />
      )}

      <h2 className={styles.section}>Systems</h2>
      <SystemsTable
        rows={rows}
        disabled={setMode.isPending}
        onMode={(system, mode) => setMode.mutate({ system, mode }, { onSuccess: refresh })}
      />

      <h2 className={styles.section}>Sync</h2>
      {!connected ? (
        <Muted>Plug the device in to see what a sync would do.</Muted>
      ) : p ? (
        <PlanLine
          plan={{
            send: p.send,
            update: p.update,
            remove: p.remove,
            unchanged: p.unchanged,
            unknownSystems: p.unknown_systems,
            bytes: p.bytes,
          }}
          list={
            <PlanDetailList
              items={[
                ...p.send.map((o) => ({ ...o, action: 'send' as const })),
                ...p.update.map((o) => ({ ...o, action: 'update' as const })),
                ...p.remove.map((o) => ({ ...o, action: 'remove' as const })),
              ]}
            />
          }
        />
      ) : plan.isError ? (
        <LoadError
          what="what a sync would do"
          message={plan.error.message}
          retrying={plan.isFetching}
          onRetry={() => void plan.refetch()}
        />
      ) : (
        <Muted>loading…</Muted>
      )}

      <h2 className={styles.section}>
        System files{' '}
        <Button small onClick={() => router.push('/system-files')}>
          Open System files
        </Button>
      </h2>
      {sysQuery.isError ? (
        <LoadError
          what="this device's system files"
          message={sysQuery.error.message}
          retrying={sysQuery.isFetching}
          onRetry={() => void sysQuery.refetch()}
        />
      ) : (
        <SysfilesLine
          connected={connected}
          line={
            sysfiles
              ? readinessLine(
                  sysfiles.systems,
                  Object.fromEntries(systems.map((x) => [x.key, x.label])),
                )
              : null
          }
        />
      )}

      <h2 className={styles.section}>History</h2>
      <RunHistory
        runs={runs.map((r) => ({
          id: r.id,
          started: r.started,
          state: r.state,
          counts: r.counts,
          bytesMoved: r.bytes_moved,
        }))}
      />

      {ask === 'rename' && (
        <PromptDialog
          title="Rename device"
          label="Name"
          initial={profile.name}
          submit="Rename"
          onCancel={() => setAsk(null)}
          onSubmit={(name) =>
            rename.mutate(name, {
              onSuccess: () => setAsk(null),
              onError: (e) => toast(e.message, true),
            })
          }
        />
      )}
      {ask === 'marker' && (
        <ConfirmDialog
          title="Write ROM-Sync.json"
          confirm="Write"
          onCancel={() => setAsk(null)}
          onConfirm={() => {
            setAsk(null)
            runJob(marker)
          }}
        >
          Write ROM-Sync.json to {profile.name} now, so it is recognised on any computer as{' '}
          {profile.name}.
        </ConfirmDialog>
      )}
      {ask === 'sync' && p && (
        <SyncConfirm
          name={profile.name}
          plan={p}
          busy={start.isPending}
          onCancel={() => setAsk(null)}
          onStart={() =>
            start.mutate(p.remove.length || null, {
              onSuccess: (j) => {
                appStore.getState().sync.begin(j.id, id, startOf(p, held))
                setAsk(null)
              },
              onError: (e) => {
                setAsk(null)
                if (e instanceof EngineError && e.code === 'sync.confirm_removals') {
                  toast('The plan changed since it was shown; check it and sync again', true)
                  void plan.refetch()
                } else toast(e.message, true)
              },
            })
          }
        />
      )}
    </PageLayout>
  )
}
