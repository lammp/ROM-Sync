'use client'

import { useEffect, useMemo, useRef, useState } from 'react'
import { Button } from '../../../components/atoms/Button/Button'
import { ReloadButton } from '../../../components/atoms/ReloadButton/ReloadButton'
import { Muted } from '../../../components/atoms/Muted/Muted'
import { JobLine, type JobState } from '../../../components/molecules/JobLine/JobLine'
import { LoadError } from '../../../components/molecules/LoadError/LoadError'
import { ConfirmDialog } from '../../../components/organisms/ConfirmDialog/ConfirmDialog'
import { SysfilesDetail } from '../../../components/organisms/SysfilesDetail/SysfilesDetail'
import { OTHERS, SysfilesList } from '../../../components/organisms/SysfilesList/SysfilesList'
import {
  SysfilesOthers,
  strayKey,
  type Stray,
} from '../../../components/organisms/SysfilesOthers/SysfilesOthers'
import { SysfilesStore } from '../../../components/organisms/SysfilesStore/SysfilesStore'
import { PageLayout } from '../../../components/templates/PageLayout/PageLayout'
import { SplitPane } from '../../../components/templates/SplitPane/SplitPane'
import { useAttached, useInventory, useProfiles } from '../../../queries/devices/devices'
import { TERMINAL, useJob } from '../../../queries/job/job'
import { useAnnounce } from '../../../queries/meta/meta'
import { useSystems } from '../../../queries/library/library'
import { useSettings } from '../../../queries/settings/settings'
import {
  useAfterSysfiles,
  useRemoveOther,
  useStage,
  useStoreSysfiles,
  useSurvey,
  useSysReport,
  useUnstage,
} from '../../../queries/sysfiles/sysfiles'
import { appStore, useAppStore } from '../../../store/store'
import { detailOf, heldBySystem, stageRoot } from './model'

const toast = (text: string, bad = false) =>
  appStore.getState().ui.toast(text, bad ? 'bad' : 'info')

const item = (s: Stray) =>
  s.kind === 'folder' ? `the folder ${s.path}/${s.name}` : `${s.path}/${s.name}`

/** What a finished job did to a device's files, in words. */
function said(kind: string, result: Readonly<Record<string, number>> | null): string {
  const r = result ?? {}
  if (r.entries !== undefined) return `Read ${r.entries.toLocaleString()} entries from the device`
  if (r.placed !== undefined)
    return `Placed ${r.placed.toLocaleString()} file${r.placed === 1 ? '' : 's'}`
  if (r.removed !== undefined)
    return `Removed ${r.removed.toLocaleString()} item${r.removed === 1 ? '' : 's'}`
  return `${kind} done`
}

/** A time of day as the page says it: 14:05:09. */
const clock = (at: number) => new Date(at).toTimeString().slice(0, 8)

/**
 * The system files page (F11-S33). With a device chosen and plugged in: its
 * systems, each system's files, and the stray files under the staging root.
 * With none: the store's copy of every file the registry knows.
 */
export function SystemFilesView() {
  const deviceId = useAppStore((s) => s.selection.device)
  const picked = useAppStore((s) => s.ui.system)
  const profile = useProfiles().data?.find((p) => p.id === deviceId) ?? null
  const device = useAttached().data?.devices.find(
    (d) => deviceId !== null && d.profile?.id === deviceId,
  )
  const ref = device?.ref ?? null
  const report = useSysReport(ref)
  const store = useStoreSysfiles()
  const systems = useSystems().data
  const inventory = useInventory(deviceId).data
  const storeRoot = useSettings().data?.find((s) => s.key === 'store.root')?.value
  const survey = useSurvey(ref ?? '')
  const stage = useStage(ref ?? '')
  const unstage = useUnstage(ref ?? '')
  const removeOther = useRemoveOther(ref ?? '')
  const after = useAfterSysfiles(ref)
  const announce = useAnnounce()
  const syncing = useAppStore((s) => s.sync.running?.device === deviceId && deviceId !== null)
  const [work, setWork] = useState<{ job: string; what: string } | null>(null)
  const [asking, setAsking] = useState<Stray | null>(null)
  const job = useJob(work?.job ?? null).data

  const labels = useMemo(
    () => Object.fromEntries((systems ?? []).map((s) => [s.key, s.label])),
    [systems],
  )
  const inStore = useMemo(() => new Map((systems ?? []).map((s) => [s.key, s.games])), [systems])
  const held = useMemo(() => heldBySystem(inventory ?? []), [inventory])

  const ended = useRef<string | null>(null)
  useEffect(() => {
    if (!job || !TERMINAL.has(job.state) || ended.current === job.id) return
    ended.current = job.id
    if (job.state === 'failed') announce(job, job.error_message ?? 'The job failed', true)
    else announce(job, said(job.kind, job.result))
    after()
  }, [job, after, announce])

  const busy = work !== null && (job === undefined || !TERMINAL.has(job.state))
  const start = (
    what: string,
    run: (done: { onSuccess: (j: { id: string }) => void; onError: (e: Error) => void }) => void,
  ) => {
    if (syncing) {
      toast('Wait for the sync to finish')
      return
    }
    run({
      onSuccess: (j) => setWork({ job: j.id, what }),
      onError: (e) => toast(e.message, true),
    })
  }

  if (!deviceId || !ref) {
    const root = typeof storeRoot === 'string' ? storeRoot : null
    return (
      <PageLayout
        heading="System files in the store"
        actions={
          <>
            {store.dataUpdatedAt > 0 && <Muted>{`checked ${clock(store.dataUpdatedAt)}`}</Muted>}
            <ReloadButton
              label="Check the bios folder again"
              busy={store.isFetching}
              onClick={() => void store.refetch()}
            />
          </>
        }
      >
        {root && <Muted>{root}\bios</Muted>}
        <p>
          <Muted>
            {deviceId && profile
              ? `Plug ${profile.name} in to see what its emulators have and need.`
              : 'Pick a device in the header to see what its emulators have and need.'}{' '}
            The app checks and places these files; it never generates them.
          </Muted>
        </p>
        {store.isError ? (
          <LoadError
            what="the store's system files"
            message={store.error.message}
            retrying={store.isFetching}
            onRetry={() => void store.refetch()}
          />
        ) : store.isPending ? (
          <Muted>checking…</Muted>
        ) : (
          <SysfilesStore
            items={(store.data ?? []).map((i) => ({ ...i, label: labels[i.system] ?? i.system }))}
          />
        )}
      </PageLayout>
    )
  }

  const data = report.data
  const rows = (data?.systems ?? []).map((s) => detailOf(s, labels, inStore, held))
  const active =
    picked === OTHERS || rows.some((r) => r.key === picked)
      ? picked
      : (rows.find((r) => r.onDevice.n > 0)?.key ?? rows[0]?.key ?? null)
  const chosen = rows.find((r) => r.key === active)
  const root = stageRoot(data?.systems ?? [])

  return (
    <PageLayout
      heading={`${profile?.name ?? 'Device'}: system files`}
      actions={
        <>
          <Muted>
            {data?.surveyed_at
              ? `device read ${data.surveyed_at.slice(0, 16).replace('T', ' ')}`
              : 'device not read yet'}
          </Muted>
          <Button
            small
            disabled={busy}
            title="Read the staging and emulator folders on the device (read-only)"
            onClick={() => start('survey', (cb) => survey.mutate(undefined, cb))}
          >
            Refresh from device
          </Button>
          <ReloadButton
            label="Check the bios folder again"
            busy={report.isFetching}
            onClick={() => void report.refetch()}
          />
        </>
      }
    >
      <Muted>
        Add or Update copies a system&apos;s files into {root}/&lt;system&gt; on the device; you
        install them from there with the emulator&apos;s own menus. Installed shows what the
        emulator actually reads.
      </Muted>
      {job && (
        <JobLine
          state={job.state as JobState}
          progress={job.progress}
          result={job.result}
          error={job.error_message}
        />
      )}
      {report.isPending ? (
        <Muted>checking…</Muted>
      ) : report.isError ? (
        <LoadError
          what="this device's system files"
          message={report.error.message}
          retrying={report.isFetching}
          onRetry={() => void report.refetch()}
        />
      ) : (
        <SplitPane
          listLabel="Systems"
          list={
            <SysfilesList
              systems={rows.map((r) => ({
                key: r.key,
                label: r.label,
                state: r.readiness,
                count: r.onDevice.n,
              }))}
              others={data?.others.length ?? 0}
              stageRoot={root}
              active={active}
              onSelect={(key) => appStore.getState().ui.pickSystem(key)}
            />
          }
        >
          {active === OTHERS ? (
            <SysfilesOthers
              others={data?.others ?? []}
              stageRoot={root}
              busy={busy && work?.what.startsWith('other:') ? work.what.slice(6) : busy ? '' : null}
              onRemove={setAsking}
            />
          ) : chosen ? (
            <SysfilesDetail
              system={chosen}
              busy={busy}
              onStage={() => start(`stage:${chosen.key}`, (cb) => stage.mutate(chosen.key, cb))}
              onUnstage={() =>
                start(`unstage:${chosen.key}`, (cb) => unstage.mutate(chosen.key, cb))
              }
            />
          ) : (
            <Muted>No systems need files.</Muted>
          )}
        </SplitPane>
      )}
      {asking && (
        <ConfirmDialog
          title={`Remove ${asking.name}`}
          confirm="Remove"
          danger
          onCancel={() => setAsking(null)}
          onConfirm={() => {
            const stray = asking
            setAsking(null)
            start(`other:${strayKey(stray)}`, (cb) =>
              removeOther.mutate({ path: stray.path, name: stray.name }, cb),
            )
          }}
        >
          Delete {item(asking)} from {profile?.name ?? 'the device'}. It belongs to no system&apos;s
          set.
        </ConfirmDialog>
      )}
    </PageLayout>
  )
}
