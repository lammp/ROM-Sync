/**
 * Bytes, sizes and estimates as text (F11-S13), version 1's fmtB, parseSize
 * and fmtEta ported exactly, pinned by the F0 format corpus.
 */

const UNITS = ['B', 'KB', 'MB', 'GB', 'TB'] as const

const MULTIPLIER: Readonly<Record<string, number>> = {
  b: 1,
  k: 1024,
  kb: 1024,
  m: 1048576,
  mb: 1048576,
  g: 1073741824,
  gb: 1073741824,
  t: 2 ** 40,
  tb: 2 ** 40,
}

const SIZE = /^([\d.]+)\s*(b|kb|mb|gb|tb|k|m|g|t)?$/

/** Bytes in binary units: two decimals under ten, one above, none for bare bytes; "?" when unknown. */
export function formatBytes(n: number | null | undefined): string {
  if (n == null) return '?'
  if (n < 0) return '-' + formatBytes(-n)
  let value = n
  let unit = 0
  while (value >= 1024 && unit < UNITS.length - 1) {
    value /= 1024
    unit++
  }
  return `${unit ? value.toFixed(value < 10 ? 2 : 1) : value} ${UNITS[unit]}`
}

/** "10 MB", "512k", "1.5g" to bytes, binary units, rounded; null when it is not a size. */
export function parseSize(text: unknown): number | null {
  const m = SIZE.exec(String(text).trim().toLowerCase())
  if (!m) return null
  return Math.round(parseFloat(m[1] ?? '') * (MULTIPLIER[m[2] ?? 'b'] ?? 1))
}

/** Seconds left as "42 s", "7 min" or "1.5 h"; an ellipsis when it cannot be known yet. */
export function formatEta(seconds: number | null | undefined): string {
  if (seconds == null || !Number.isFinite(seconds)) return '…'
  if (seconds < 60) return `${Math.max(1, Math.round(seconds))} s`
  if (seconds < 3600) return `${Math.round(seconds / 60)} min`
  return `${(seconds / 3600).toFixed(1)} h`
}
