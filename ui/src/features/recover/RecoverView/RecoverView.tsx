'use client'

import { Muted } from '../../../components/atoms/Muted/Muted'
import { RecoverTable } from '../../../components/organisms/RecoverTable/RecoverTable'
import { PageLayout } from '../../../components/templates/PageLayout/PageLayout'
import { useAttached, useSelections } from '../../../queries/devices/devices'
import { useSystems } from '../../../queries/library/library'
import { useRecoverLists } from '../../../queries/recover/recover'
import { orphans } from './model'

/**
 * The recover page (F11-S39): for each device plugged in, what it holds that
 * the store has no copy of, read from what was last read of the device, and
 * what the next sync will do to each.
 */
export function RecoverView() {
  const devices = (useAttached().data?.devices ?? []).filter((d) => d.profile !== null)
  const lists = useRecoverLists(devices.map((d) => d.ref))
  const selections = useSelections(devices.map((d) => d.profile?.id ?? ''))
  const labels = Object.fromEntries((useSystems().data ?? []).map((s) => [s.key, s.label]))
  return (
    <PageLayout heading="Recover">
      <Muted>
        What a device holds that the store has no copy of. A sync makes the device match the store,
        so anything here in a system the device manages goes at the next sync.
      </Muted>
      {devices.length === 0 && <p>Plug a device in to see what only it holds.</p>}
      {devices.map((d, i) => {
        const name = d.profile?.name ?? d.description
        const list = lists[i]
        return (
          <section key={d.ref} aria-labelledby={`recover-${i}`}>
            <h2 id={`recover-${i}`}>{name}</h2>
            {list?.isError ? (
              <Muted>{list.error.message}</Muted>
            ) : list?.data ? (
              <RecoverTable
                device={name}
                items={orphans(list.data, selections[i]?.data ?? null, labels)}
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
