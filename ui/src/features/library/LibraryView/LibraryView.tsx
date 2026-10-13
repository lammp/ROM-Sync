'use client'

import { useRouter } from 'next/navigation'
import { useCallback, useDeferredValue, useMemo, useState } from 'react'
import { GameRow } from '../../../components/molecules/GameRow/GameRow'
import { LoadError } from '../../../components/molecules/LoadError/LoadError'
import { GameTile } from '../../../components/molecules/GameTile/GameTile'
import { JobLine, type JobState } from '../../../components/molecules/JobLine/JobLine'
import { CapacityMeter } from '../../../components/molecules/CapacityMeter/CapacityMeter'
import { SyncControl } from '../../../components/molecules/SyncControl/SyncControl'
import { ConfirmDialog } from '../../../components/organisms/ConfirmDialog/ConfirmDialog'
import { DetailPanel } from '../../../components/organisms/DetailPanel/DetailPanel'
import { FilterSidebar } from '../../../components/organisms/FilterSidebar/FilterSidebar'
import { LibraryToolbar } from '../../../components/organisms/LibraryToolbar/LibraryToolbar'
import { SelectionSummary } from '../../../components/organisms/SelectionSummary/SelectionSummary'
import { TwinCompareCard } from '../../../components/organisms/TwinCompareCard/TwinCompareCard'
import { VirtualGameGrid } from '../../../components/organisms/VirtualGameGrid/VirtualGameGrid'
import { LibraryLayout } from '../../../components/templates/LibraryLayout/LibraryLayout'
import { read } from '../../../lib/capacity/capacity'
import { formatBytes } from '../../../lib/format/format'
import { deviceKey, isOverride, isSelected, onDeviceKeys } from '../../../lib/selection/selection'
import { buildTwins } from '../../../lib/twins/twins'
import {
  attachedFor,
  useAttached,
  useCapacity,
  useClearSelection,
  useInventory,
  usePlan,
  useProfiles,
  useRefreshCapacity,
  useSelection,
  useSetGames,
} from '../../../queries/devices/devices'
import { useJob } from '../../../queries/job/job'
import { useLibrary, useGame, useRematch, type ListedGame } from '../../../queries/library/library'
import { thresholds, useSettings } from '../../../queries/settings/settings'
import { useTagChange, useTags } from '../../../queries/tags/tags'
import { appStore, useAppStore } from '../../../store/store'
import {
  chips,
  facetViews,
  narrow,
  selectionCounts,
  sizeBounds,
  sizeFromPair,
  sizeFromText,
  sizePair,
  yearFromPair,
  yearFromText,
  yearPair,
  YEAR_MAX,
  YEAR_MIN,
  type DeviceState,
} from './model'

type Ask = 'clear-shown' | 'select-shown' | 'clear-all' | null

const NO_GAMES: readonly ListedGame[] = []
const NO_SYSTEMS: Readonly<Record<string, string>> = {}

/** The library: filters, the grid, and the game in view, bound to the store and the engine. */
export function LibraryView() {
  const router = useRouter()
  const library = useLibrary()
  const settings = useSettings()
  const f = useAppStore((s) => s.filters)
  const query = useDeferredValue(f.query)
  const { layout, tile, current } = useAppStore((s) => s.library)
  const twinOpen = useAppStore((s) => s.ui.twin)
  const deviceId = useAppStore((s) => s.selection.device)
  const running = useAppStore((s) => s.sync.running)
  const profile = (useProfiles().data ?? []).find((p) => p.id === deviceId) ?? null
  const attached = attachedFor(useAttached().data?.devices ?? [], profile?.id ?? null)
  const ref = attached ? attached.ref : null
  const selection = useSelection(deviceId).data ?? null
  const inventory = useInventory(deviceId).data ?? null
  const plan = usePlan(ref).data ?? null
  const capacity = useCapacity(ref).data ?? null
  const setGames = useSetGames(deviceId ?? '')
  const clearAll = useClearSelection(deviceId ?? '')
  const refresh = useRefreshCapacity(ref)
  const [ask, setAsk] = useState<Ask>(null)
  const [rematchJob, setRematchJob] = useState<string | null>(null)
  const rematchView = useJob(rematchJob).data

  const games = library.data?.games ?? NO_GAMES
  const systems = library.data?.systems ?? NO_SYSTEMS
  const device: DeviceState = useMemo(
    () => (selection && inventory ? { selection, onDevice: onDeviceKeys(inventory) } : null),
    [selection, inventory],
  )
  const values = useMemo(() => ({ ...f, query }), [f, query])
  const { filtered } = useMemo(() => narrow(games, values, device), [games, values, device])
  const twins = useMemo(() => buildTwins(games), [games])
  const bounds = useMemo(() => sizeBounds(games), [games])
  const shown = filtered.shown as readonly ListedGame[]
  const counts = device ? selectionCounts(games, shown, device) : null

  const actions = appStore.getState()
  const toggle = useCallback(
    (g: ListedGame) => {
      if (!device) return
      setGames.mutate({ gameIds: [g.id], include: !isSelected(device.selection, g) })
    },
    [device, setGames],
  )

  const deviceBadge = (g: ListedGame) =>
    device && profile
      ? {
          name: profile.name,
          selected: isSelected(device.selection, g),
          override: isOverride(device.selection, g),
          onDevice: device.onDevice.has(deviceKey(g.system, g.name)),
          onToggle: () => toggle(g),
        }
      : undefined

  const twinBadge = (g: ListedGame) => {
    const t = twins.get(g.id)
    if (!t) return undefined
    const dupe = device
      ? isSelected(device.selection, g) && t.some((x) => isSelected(device.selection, x.game))
      : false
    const where = [...new Set(t.map((x) => x.game.sysLabel))].join(', ')
    return {
      dupe,
      label: dupe ? `Already selected on ${where}` : `Also in the library on ${where}`,
      onCompare: () => actions.ui.compare(g.id),
    }
  }

  const open = useMemo(() => games.find((g) => g.id === current) ?? null, [games, current])
  const detail = useGame(open?.id ?? null).data
  const tags = useTags(open?.id ?? null).data?.tags ?? []
  const tagChange = useTagChange(open?.id ?? 0)
  const rematch = useRematch(open?.id ?? 0)

  const versions = open
    ? [open, ...(twins.get(open.id) ?? []).map((t) => t.game)].map((g) => ({
        id: g.id,
        sysLabel: g.sysLabel,
        year: g.year,
        selected: device ? isSelected(device.selection, g) : false,
        loose: (twins.get(open.id) ?? []).find((t) => t.game.id === g.id)?.loose ?? false,
      }))
    : []

  const asTwin = (g: ListedGame) => ({
    title: g.title,
    name: g.name,
    sysLabel: g.sysLabel,
    year: g.year,
    size: g.size,
    cover: g.coverUrl,
  })
  const twinHost = twinOpen != null ? games.find((g) => g.id === twinOpen) : undefined
  const compare = twinHost
    ? [
        {
          id: twinHost.id,
          game: asTwin(twinHost),
          loose: false,
          selected: device ? isSelected(device.selection, twinHost) : false,
          onDevice: device ? device.onDevice.has(deviceKey(twinHost.system, twinHost.name)) : false,
          action: { kind: 'self' as const },
        },
        ...(twins.get(twinHost.id) ?? []).map((t) => {
          const sel = device ? isSelected(device.selection, t.game) : false
          const hostSel = device ? isSelected(device.selection, twinHost) : false
          return {
            id: t.game.id,
            game: asTwin(t.game),
            loose: t.loose,
            selected: sel,
            onDevice: device ? device.onDevice.has(deviceKey(t.game.system, t.game.name)) : false,
            onOpen: () => {
              actions.library.open(t.game.id)
              actions.ui.compare(null)
            },
            action: !device
              ? ({ kind: 'none' } as const)
              : sel
                ? ({ kind: 'kept' } as const)
                : hostSel
                  ? {
                      kind: 'switch' as const,
                      from: twinHost.sysLabel,
                      onSwitch: () => {
                        setGames.mutate({ gameIds: [twinHost.id], include: false })
                        setGames.mutate({ gameIds: [t.game.id], include: true })
                      },
                    }
                  : {
                      kind: 'select' as const,
                      onSelect: () => setGames.mutate({ gameIds: [t.game.id], include: true }),
                    },
          }
        }),
      ]
    : []

  const reading =
    device && profile
      ? read(
          {
            capacity: capacity?.total ?? profile.capacity,
            free: capacity?.free ?? profile.free,
            connected: attached !== null,
            selected: counts?.selected ?? { n: 0, bytes: 0 },
            plan: plan?.bytes ?? null,
          },
          thresholds(settings.data),
        )
      : null

  const confirmText: Record<
    Exclude<Ask, null>,
    { title: string; body: string; confirm: string; danger: boolean; run: () => void }
  > = {
    'clear-shown': {
      title: 'Clear the games shown',
      body: `Deselect the ${counts?.shown.selected ?? 0} selected games among those shown, for ${profile?.name ?? ''}. Nothing on the device changes until you sync.`,
      confirm: 'Clear shown',
      danger: true,
      run: () =>
        setGames.mutate({
          gameIds: shown.filter((g) => device && isSelected(device.selection, g)).map((g) => g.id),
          include: false,
        }),
    },
    'select-shown': {
      title: 'Select the games shown',
      body: `Select the ${counts?.shown.unselected ?? 0} games shown that are not selected, for ${profile?.name ?? ''}.`,
      confirm: 'Select shown',
      danger: false,
      run: () =>
        setGames.mutate({
          gameIds: shown
            .filter((g) => !(device && isSelected(device.selection, g)))
            .map((g) => g.id),
          include: true,
        }),
    },
    'clear-all': {
      title: 'Clear the whole selection',
      body: `Deselect every game for ${profile?.name ?? ''}. Nothing on the device changes until you sync.`,
      confirm: 'Clear all',
      danger: true,
      run: () => clearAll.mutate(),
    },
  }

  const rematchLine = rematchView ? (
    <JobLine
      state={rematchView.state as JobState}
      progress={rematchView.progress}
      result={rematchView.result}
      error={rematchView.error_message}
    />
  ) : null

  return (
    <>
      <LibraryLayout
        sidebar={
          <FilterSidebar
            active={chips(f, systems, {
              toggle: actions.filters.toggle,
              clearSize: () => actions.filters.setRange('size', { min: null, max: null }),
              clearYear: () => actions.filters.setRange('year', { min: null, max: null }),
              clearRating: () => actions.filters.setRating(0),
            })}
            onClearAll={actions.filters.clear}
            onSmart={actions.filters.setQuery}
            rating={f.rating}
            onRating={actions.filters.setRating}
            facets={facetViews(filtered, f, f.expanded, f.collapsed, systems)}
            onToggle={actions.filters.toggle}
            onFold={(facet) => actions.filters.setUnfolded(facet, !f.expanded.includes(facet))}
            onCollapse={actions.filters.setCollapsed}
            onClear={(facet) => f.chosen[facet].forEach((v) => actions.filters.toggle(facet, v))}
            size={{
              min: 0,
              max: 1000,
              gap: 10,
              value: sizePair(f, bounds),
              onChange: (p) => actions.filters.setRange('size', sizeFromPair(p, bounds)),
              valueText: (v) => {
                const b = sizeFromPair({ lo: v, hi: v }, bounds).min
                return b == null ? 'no limit' : formatBytes(b)
              },
              exact: {
                min: f.size.min == null ? '' : formatBytes(f.size.min),
                max: f.size.max == null ? '' : formatBytes(f.size.max),
                onMin: (t) =>
                  actions.filters.setRange('size', { min: sizeFromText(t), max: f.size.max }),
                onMax: (t) =>
                  actions.filters.setRange('size', { min: f.size.min, max: sizeFromText(t) }),
                minPlaceholder: 'min e.g. 10mb',
                maxPlaceholder: 'max e.g. 2gb',
              },
            }}
            year={{
              min: YEAR_MIN,
              max: YEAR_MAX,
              gap: 0,
              value: yearPair(f),
              onChange: (p) => actions.filters.setRange('year', yearFromPair(p)),
              valueText: (v) => (v <= YEAR_MIN || v >= YEAR_MAX ? 'no limit' : String(v)),
              exact: {
                min: f.year.min == null ? '' : String(f.year.min),
                max: f.year.max == null ? '' : String(f.year.max),
                onMin: (t) =>
                  actions.filters.setRange('year', { min: yearFromText(t), max: f.year.max }),
                onMax: (t) =>
                  actions.filters.setRange('year', { min: f.year.min, max: yearFromText(t) }),
                minPlaceholder: 'from',
                maxPlaceholder: 'to',
              },
            }}
            flags={f.flags}
            onFlag={actions.filters.setFlag}
            device={device !== null}
          />
        }
        panel={
          open && (
            <DetailPanel
              game={{
                id: open.id,
                title: open.title,
                name: open.name,
                cover: open.coverUrl,
                year: open.year,
                rating: open.rating,
                votes: open.votes,
                size: open.size,
                kind: open.kind,
                files: open.files,
                regions: open.regions,
                summary: detail?.summary ?? null,
                matched: open.matched,
                igdbName: open.igdb_name,
                confidence: detail?.confidence ?? null,
                genres: open.genres,
              }}
              versions={versions}
              onPickVersion={(id) => {
                if (device && isSelected(device.selection, open)) {
                  setGames.mutate({ gameIds: [open.id], include: false })
                  setGames.mutate({ gameIds: [id], include: true })
                }
                actions.library.open(id)
              }}
              device={
                deviceBadge(open) && profile
                  ? {
                      name: profile.name,
                      selected: isSelected(device!.selection, open),
                      onToggle: () => toggle(open),
                    }
                  : undefined
              }
              tags={tags
                .filter((t) => t.state !== 'rejected')
                .map((t) => ({
                  tag: t.tag,
                  kind: t.kind,
                  state: t.state === 'proposed' ? 'proposed' : 'accepted',
                }))}
              onRemoveTag={(t) => tagChange.mutate({ op: 'remove', tag: t.tag, kind: t.kind })}
              onDecideTag={(t, accept) =>
                tagChange.mutate({ op: 'decide', tag: t.tag, kind: t.kind, accept })
              }
              onAddTag={(t) => tagChange.mutate({ op: 'add', tag: t.tag, kind: t.kind })}
              onRematch={(r) => rematch.mutate(r, { onSuccess: (job) => setRematchJob(job.id) })}
              rematch={rematchLine}
              onClose={() => actions.library.close()}
            />
          )
        }
      >
        <LibraryToolbar
          shown={{ n: shown.length, bytes: shown.reduce((a, g) => a + g.size, 0) }}
          total={games.length}
          sort={f.sort}
          onSort={actions.filters.setSort}
          view={layout}
          onView={actions.library.setLayout}
          tile={tile}
          onTile={actions.library.setTile}
          selection={
            counts && profile ? (
              <SelectionSummary
                device={{
                  name: profile.name,
                  href: `/devices?id=${encodeURIComponent(profile.id)}`,
                }}
                selected={counts.selected}
                onDevice={counts.onDevice}
                shown={counts.shown}
                sync={
                  <SyncControl
                    state={
                      running !== null && running.device === profile.id
                        ? { kind: 'running', reading: running.reading }
                        : ref
                          ? {
                              kind: 'idle',
                              onSync: () =>
                                router.push(`/devices?id=${encodeURIComponent(profile.id)}`),
                            }
                          : { kind: 'disabled', reason: 'Plug the device in to sync' }
                    }
                  />
                }
                onClearShown={() => setAsk('clear-shown')}
                onSelectShown={() => setAsk('select-shown')}
                onClearAll={() => setAsk('clear-all')}
                selectionKey={selection}
                onSettled={refresh}
              />
            ) : undefined
          }
          capacity={reading ? <CapacityMeter reading={reading} /> : undefined}
        />
        <VirtualGameGrid
          items={shown}
          itemKey={(g) => g.id}
          view={layout}
          tile={tile}
          layoutKey={`${values.query}|${f.sort}|${shown.length}`}
          label={`Games, ${shown.length.toLocaleString()} shown`}
          empty={
            library.isPending ? (
              'Reading the library…'
            ) : library.isError ? (
              <LoadError
                what="the library"
                message={library.error.message}
                retrying={library.isFetching}
                onRetry={() => void library.refetch()}
              />
            ) : (
              'Nothing matches these filters.'
            )
          }
          renderItem={(g) =>
            layout === 'grid' ? (
              <GameTile
                game={{
                  id: g.id,
                  title: g.title,
                  name: g.name,
                  system: g.system,
                  year: g.year,
                  rating: g.rating,
                  cover: g.coverUrl,
                }}
                current={g.id === current}
                onOpen={() => actions.library.open(g.id)}
                device={deviceBadge(g)}
                twin={twinBadge(g)}
              />
            ) : (
              <GameRow
                game={{
                  id: g.id,
                  title: g.title,
                  name: g.name,
                  system: g.system,
                  sysLabel: g.sysLabel,
                  year: g.year,
                  rating: g.rating,
                  cover: g.coverUrl,
                  size: g.size,
                }}
                current={g.id === current}
                onOpen={() => actions.library.open(g.id)}
                device={deviceBadge(g)}
                twin={twinBadge(g)}
              />
            )
          }
        />
      </LibraryLayout>
      {twinHost && compare.length > 1 && (
        <TwinCompareCard
          matchedOn={twinHost.igdb_name}
          rows={compare}
          onClose={() => actions.ui.compare(null)}
        />
      )}
      {ask && (
        <ConfirmDialog
          title={confirmText[ask].title}
          confirm={confirmText[ask].confirm}
          danger={confirmText[ask].danger}
          onCancel={() => setAsk(null)}
          onConfirm={() => {
            confirmText[ask].run()
            setAsk(null)
          }}
        >
          {confirmText[ask].body}
        </ConfirmDialog>
      )}
    </>
  )
}
