'use client'

import { useEffect, useRef, useState } from 'react'
import { Muted } from '../../../components/atoms/Muted/Muted'
import { JobLine, type JobState } from '../../../components/molecules/JobLine/JobLine'
import { LoadError } from '../../../components/molecules/LoadError/LoadError'
import {
  RecoverTable,
  orphanKey,
  type Orphan,
} from '../../../components/organisms/RecoverTable/RecoverTable'
import { PageLayout } from '../../../components/templates/PageLayout/PageLayout'
import { useAttached, useSelections } from '../../../queries/devices/devices'
import { TERMINAL, useJob } from '../../../queries/job/job'
import { useAnnounce } from '../../../queries/meta/meta'
import { useLibraryJob, useSystems } from '../../../queries/library/library'
import { useAfterRecover, useRecover, useRecoverLists } from '../../../queries/recover/recover'
import { appStore, useAppStore } from '../../../store/store'
import { orphans } from './model'

const toast = (text: string, bad = false) =>
  appStore.getState().ui.toast(text, bad ? 'bad' : 'info')

type Work = {
  readonly stage: 'recover' | 'scan'
  readonly job: string
  readonly key: string
  readonly name: string
}

/** Recovers into the store from one device, then reads the store again so the game is in the library. */
function DeviceRecover({
  name,
  deviceRef,
  deviceId,
  items,
  clashes,
  onClash,
}: {
  name: string
  deviceRef: string
  deviceId: string
  items: readonly Orphan[]
  clashes: ReadonlySet<string>
  onClash: (key: string) => void
}) {
  const recover = useRecover(deviceRef)
  const scan = useLibraryJob('/api/v1/library/scan')
  const after = useAfterRecover()
  const announce = useAnnounce()
  const syncing = useAppStore((s) => s.sync.running?.device === deviceId)
  const [work, setWork] = useState<Work | null>(null)
  const job = useJob(work?.job ?? null).data
  const ended = useRef<string | null>(null)

  useEffect(() => {
    if (!work || !job || !TERMINAL.has(job.state) || ended.current === job.id) return
    ended.current = job.id
    if (job.state !== 'done') {
      if (job.error_code === 'store.would_overwrite') onClash(work.key)
      announce(job, job.error_message ?? `${work.name} was not recovered`, true)
      return
    }
    if (work.stage === 'recover') {
      announce(job, `${work.name} placed in the store; reading the store again`)
      // rescan_after_place: the placed game appears in the library without a manual step
      scan.mutate(undefined, {
        onSuccess: (j) => setWork({ ...work, stage: 'scan', job: j.id }),
        onError: (e) => {
          toast(e.message, true)
          after()
        },
      })
      return
    }
    announce(job, `${work.name} is in the library`)
    after()
  }, [work, job, scan, after, onClash, announce])

  return (
    <>
      <RecoverTable
        device={name}
        items={items.map((o) => (clashes.has(orphanKey(o)) ? { ...o, clash: true } : o))}
        busy={work && (!job || !TERMINAL.has(job.state)) ? work.key : null}
        onRecover={
          syncing
            ? undefined
            : (o) =>
                recover.mutate(
                  { system: o.system, name: o.name },
                  {
                    onSuccess: (j) =>
                      setWork({ stage: 'recover', job: j.id, key: orphanKey(o), name: o.name }),
                    onError: (e) => toast(e.message, true),
                  },
                )
        }
      />
      {job && work && !TERMINAL.has(job.state) && (
        <JobLine
          state={job.state as JobState}
          progress={job.progress}
          result={job.result}
          error={job.error_message}
        />
      )}
    </>
  )
}

/**
 * The recover page (F11-S39, S40): for each device plugged in, what it holds
 * that the store has no copy of, what the next sync will do to each, and
 * Recover, which pulls a file back into the store, never over one the store
 * already has, and then reads the store again.
 */
export function RecoverView() {
  const devices = (useAttached().data?.devices ?? []).filter((d) => d.profile !== null)
  const lists = useRecoverLists(devices.map((d) => d.ref))
  const selections = useSelections(devices.map((d) => d.profile?.id ?? ''))
  const labels = Object.fromEntries((useSystems().data ?? []).map((s) => [s.key, s.label]))
  const [clashes, setClashes] = useState<ReadonlySet<string>>(new Set())
  return (
    <PageLayout heading="Recover">
      <Muted>
        What a device holds that the store has no copy of. A sync makes the device match the store,
        so anything here in a system the device manages goes at the next sync. Recover copies a file
        back into the store; it never replaces a file the store already has.
      </Muted>
      {devices.length === 0 && <p>Plug a device in to see what only it holds.</p>}
      {devices.map((d, i) => {
        const name = d.profile?.name ?? d.description
        const list = lists[i]
        return (
          <section key={d.ref} aria-labelledby={`recover-${i}`}>
            <h2 id={`recover-${i}`}>{name}</h2>
            {list?.isError ? (
              <LoadError
                what={`what ${name} holds`}
                message={list.error.message}
                retrying={list.isFetching}
                onRetry={() => void list.refetch()}
              />
            ) : list?.data ? (
              <DeviceRecover
                name={name}
                deviceRef={d.ref}
                deviceId={d.profile?.id ?? ''}
                items={orphans(list.data, selections[i]?.data ?? null, labels)}
                clashes={clashes}
                onClash={(key) => setClashes((c) => new Set([...c, key]))}
              />
            ) : (
              <Muted>checking…</Muted>
            )}
          </section>
        )
      })}
    </PageLayout>
  )
}
