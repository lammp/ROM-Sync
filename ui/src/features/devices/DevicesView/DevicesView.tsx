'use client'

import { useRouter } from 'next/navigation'
import { useState } from 'react'
import { Button } from '../../../components/atoms/Button/Button'
import { Muted } from '../../../components/atoms/Muted/Muted'
import {
  DeviceCard,
  type DeviceCardProps,
  type Space,
} from '../../../components/organisms/DeviceCard/DeviceCard'
import { NewProfileDialog } from '../../../components/organisms/NewProfileDialog/NewProfileDialog'
import { CardGrid } from '../../../components/templates/CardGrid/CardGrid'
import { PageLayout } from '../../../components/templates/PageLayout/PageLayout'
import { isSelected, onDeviceKeys } from '../../../lib/selection/selection'
import {
  useAdopt,
  useAttached,
  useCapacities,
  useCreateProfile,
  useInventories,
  useProfiles,
  useSelections,
  type Attached,
  type Profile,
} from '../../../queries/devices/devices'
import { useLibrary } from '../../../queries/library/library'
import { appStore } from '../../../store/store'

const deviceHref = (id: string) => `/devices?id=${encodeURIComponent(id)}`

/** A profile's space: live when it is attached, else what was last seen. */
function spaceOf(profile: Profile, live: { total: number; free: number } | undefined): Space {
  if (live) return live
  return profile.capacity != null && profile.free != null
    ? { total: profile.capacity, free: profile.free }
    : null
}

/** The devices page (F11-S31): every profile, and every device plugged in without one. */
export function DevicesView() {
  const router = useRouter()
  const attached = useAttached()
  const profiles = useProfiles().data ?? []
  const games = useLibrary().data?.games ?? []
  const ids = profiles.map((p) => p.id)
  const selections = useSelections(ids)
  const inventories = useInventories(ids)
  const devices = attached.data?.devices ?? []
  const blocked = attached.data?.blocked ?? []
  const capacities = useCapacities(devices.map((d) => d.ref))
  const create = useCreateProfile()
  const adopt = useAdopt()
  const [making, setMaking] = useState<Attached | null>(null)

  const live = new Map(devices.map((d, i) => [d.ref, capacities[i]?.data]))
  const here = new Map(devices.flatMap((d) => (d.profile ? [[d.profile.id, d] as const] : [])))
  const toast = (text: string, bad = false) =>
    appStore.getState().ui.toast(text, bad ? 'bad' : 'info')
  const open = (id: string) => router.push(deviceHref(id))

  const cards: (DeviceCardProps & { key: string })[] = [
    ...profiles.map((p, i): DeviceCardProps & { key: string } => {
      const device = here.get(p.id)
      const selection = selections[i]?.data
      const items = inventories[i]?.data
      const games_ = items?.filter((x) => x.system.toLowerCase() !== 'bios')
      return {
        key: `p:${p.id}`,
        variant: 'profile',
        name: p.name,
        online: device !== undefined,
        transport: device?.kind ?? p.kind,
        roms: device?.roms_root ?? p.roms_root,
        lastSeen: p.last_seen,
        space: spaceOf(p, device ? live.get(device.ref) : undefined),
        figures:
          selection && games_
            ? {
                selected: games.filter((g) => isSelected(selection, g)).length,
                onDevice: onDeviceKeys(games_).size,
                usedByGames: games_.reduce((a, x) => a + (x.size ?? 0), 0),
              }
            : null,
        onSync: () => {
          appStore.getState().selection.choose(p.id)
          open(p.id)
        },
        onContents: () => open(p.id),
        onChoose: () => {
          appStore.getState().selection.choose(p.id)
          router.push('/')
        },
      }
    }),
    ...devices
      .filter((d) => d.profile === null)
      .map((d): DeviceCardProps & { key: string } => ({
        key: `d:${d.ref}`,
        variant: 'candidate',
        label: d.description,
        transport: d.kind,
        space: live.get(d.ref) ?? null,
        state: d.has_marker
          ? {
              kind: 'foreign',
              onAdopt: () =>
                adopt.mutate(d.ref, {
                  onSuccess: (p) => {
                    toast(`Adopted ${p.name}`)
                    open(p.id)
                  },
                  onError: (e) => toast(e.message, true),
                }),
            }
          : { kind: 'new', onNew: () => setMaking(d) },
      })),
    ...blocked.map((b, i): DeviceCardProps & { key: string } => ({
      key: `b:${i}`,
      variant: 'candidate',
      label: b.description || 'A device that cannot be read',
      transport: b.kind,
      space: null,
      state: { kind: 'debugging', reason: b.reason },
    })),
  ]

  const checked = attached.dataUpdatedAt
    ? `checked ${new Date(attached.dataUpdatedAt).toLocaleTimeString()}`
    : 'looking…'

  return (
    <PageLayout
      heading="Devices"
      actions={
        <>
          <Muted>{attached.isError ? `could not look: ${attached.error.message}` : checked}</Muted>
          <Button small onClick={() => void attached.refetch()} disabled={attached.isFetching}>
            Look again
          </Button>
        </>
      }
    >
      {cards.length === 0 ? (
        <Muted>
          {attached.isPending
            ? 'looking…'
            : 'No profiles, and nothing plugged in that could be a destination.'}
        </Muted>
      ) : (
        <CardGrid label="Devices">
          {cards.map(({ key, ...card }) => (
            <li key={key}>
              <DeviceCard {...card} />
            </li>
          ))}
        </CardGrid>
      )}
      {making && (
        <NewProfileDialog
          device={making.description}
          root={making.roms_root}
          drive={making.kind === 'volume'}
          busy={create.isPending}
          error={create.error?.message}
          onCancel={() => {
            create.reset()
            setMaking(null)
          }}
          onCreate={(name, writeMarker) =>
            create.mutate(
              { ref: making.ref, name, writeMarker },
              {
                onSuccess: (p) => {
                  setMaking(null)
                  toast(`Profile ${p.name} created`)
                  open(p.id)
                },
              },
            )
          }
        />
      )}
    </PageLayout>
  )
}
