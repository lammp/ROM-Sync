/**
 * The size slider's scale (F11-S16), version 1's log mapping.
 *
 * The slider runs 0 to 1000 over the natural log of a size, from 1 KB (or
 * the smallest game, if larger) to the largest game times 1.05. Its ends
 * mean "no limit", not a value, so both map to null.
 */

export const SLIDER_MAX = 1000

export type LogBounds = { readonly min: number; readonly max: number }

/** Version 1's default before a library is loaded: 1 KB to 64 GB. */
export const DEFAULT_BOUNDS: LogBounds = { min: Math.log(1024), max: Math.log(64 * 2 ** 30) }

/** Bounds from the library's sizes, ignoring empty files. */
export function logBounds(sizes: readonly number[]): LogBounds {
  const real = sizes.filter((x) => x > 0)
  if (real.length === 0) return DEFAULT_BOUNDS
  return {
    min: Math.log(Math.max(1024, Math.min(...real))),
    max: Math.log(Math.max(...real) * 1.05),
  }
}

/** A slider position to bytes; null at either end, which is no limit. */
export function sliderToBytes(v: number, b: LogBounds): number | null {
  if (v <= 0 || v >= SLIDER_MAX) return null
  return Math.round(Math.exp(b.min + ((b.max - b.min) * v) / SLIDER_MAX))
}

/** Bytes to a slider position, sizes under 1 KB placed as 1 KB; null for no limit. */
export function bytesToSlider(bytes: number | null, b: LogBounds): number | null {
  if (bytes == null) return null
  return Math.round(((Math.log(Math.max(1024, bytes)) - b.min) / (b.max - b.min)) * SLIDER_MAX)
}
