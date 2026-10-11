/** The engine's settings, read (F10-S7), and the thresholds the capacity meter takes from them. */
import { useQuery } from '@tanstack/react-query'
import type { components } from '../../lib/api/api'
import type { Thresholds } from '../../lib/capacity/capacity'
import { unwrap, useEngine } from '../engine/engine'

export type Setting = components['schemas']['SettingItem']

export const SETTINGS_KEY = ['settings'] as const

export function useSettings() {
  const { api } = useEngine()
  return useQuery({
    queryKey: SETTINGS_KEY,
    queryFn: async ({ signal }) => unwrap(await api.GET('/api/v1/settings', { signal })).settings,
  })
}

const num = (settings: readonly Setting[], key: string, fallback: number) => {
  const v = settings.find((s) => s.key === key)?.value
  return typeof v === 'number' ? v : fallback
}

/** The meter's thresholds, from the settings registry (SPEC section 7); the registry's defaults until read. */
export function thresholds(settings: readonly Setting[] | undefined): Thresholds {
  const s = settings ?? []
  return {
    warnFraction: num(s, 'capacity.warn_fraction', 0.8),
    alarmFraction: num(s, 'capacity.alarm_fraction', 0.9),
    margin: num(s, 'plan.free_space_margin', 512 * 1024 * 1024),
  }
}
