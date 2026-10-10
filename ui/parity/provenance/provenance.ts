/**
 * Provenance: where the fixtures are, and the check that none of them carries
 * anything from the owner's library. Every corpus is synthetic or built from
 * published game titles; this is what proves it rather than asserts it.
 */
import { existsSync, readdirSync } from 'node:fs'
import { join } from 'node:path'
import { UI_ROOT } from '../v1/v1.ts'

export function findFixtures(root: string = join(UI_ROOT, 'src')): string[] {
  const found: string[] = []
  if (!existsSync(root)) return found
  const walk = (dir: string): void => {
    for (const entry of readdirSync(dir, { withFileTypes: true })) {
      const path = join(dir, entry.name)
      if (entry.isDirectory()) walk(path)
      else if (entry.name.endsWith('.json') && dir.endsWith('__fixtures__')) found.push(path)
    }
  }
  walk(root)
  return found.sort()
}

/** Every string in a value, object keys included. */
export function stringsIn(value: unknown): string[] {
  if (typeof value === 'string') return [value]
  if (value === null || typeof value !== 'object') return []
  if (Array.isArray(value)) return value.flatMap(stringsIn)
  return Object.entries(value).flatMap(([k, v]) => [k, ...stringsIn(v)])
}

const OWNER_DATA: readonly (readonly [string, RegExp])[] = [
  ['a drive path', /\b[A-Za-z]:[\\/]/],
  ['a backslash path', /\\/],
  ['a home or mount path', /\/(home|Users|mnt|media)\//],
  ['a file hash', /\b[0-9a-fA-F]{32,}\b/],
  ['a USB identifier', /\b(VID|PID)_[0-9A-Fa-f]{4}\b|\b[0-9a-f]{4}:[0-9a-f]{4}\b/],
  [
    'a game file name',
    /\.(nes|sfc|smc|gba|gbc|gb|n64|z64|v64|nds|3ds|cia|iso|chd|cue|bin|rvz|wbfs|gcz|nsp|xci|pbp|zip|7z|rar)\b/i,
  ],
  ['a library source name', /Minerva|Myrient|No-Intro|Redump|ES-DE/i],
]

/** The findings for a set of strings: empty when nothing looks like owner data. */
export function ownerData(strings: readonly string[]): string[] {
  const findings: string[] = []
  for (const s of strings) {
    for (const [what, pattern] of OWNER_DATA) if (pattern.test(s)) findings.push(`${what}: ${s}`)
  }
  return findings
}
