/**
 * The synthetic library every corpus feeds version 1.
 *
 * Titles are published game titles. Everything else is invented: ids, file
 * names, sizes, tags, ratings. Nothing comes from the owner's library, which
 * `library.test.ts` and the provenance scan both check.
 */

export type V1Tag = { readonly tag: string; readonly kind: string }

export type V1Game = {
  readonly id: number
  readonly name: string
  readonly title: string
  readonly igdb: string | null
  readonly system: string
  readonly genres: readonly string[]
  readonly tags: readonly V1Tag[]
  readonly region: string
  readonly year: number | null
  readonly size: number
  readonly rating: number | null
  readonly votes: number | null
  readonly files: number
  readonly kind: 'file' | 'folder'
  readonly matched: boolean
  readonly cover: null
  readonly mtime: number
}

export const SYSTEMS: Readonly<Record<string, string>> = {
  nes: 'Nintendo Entertainment System',
  snes: 'Super Nintendo',
  n64: 'Nintendo 64',
  gb: 'Game Boy',
  gba: 'Game Boy Advance',
  nds: 'Nintendo DS',
  n3ds: 'Nintendo 3DS',
  wii: 'Wii',
  md: 'Mega Drive',
  sms: 'Master System',
  ps2: 'PlayStation 2',
  ps3: 'PlayStation 3',
  psp: 'PlayStation Portable',
  arcade: 'Arcade',
}

/** [title, system, igdb canonical name or null, year or null] */
type Seed = readonly [string, string, string | null, number | null]

const SEEDS: readonly Seed[] = [
  // twins: a release form marker stripped, so the pair is loose
  ["The Legend of Zelda: Majora's Mask", 'n64', null, 2000],
  ["The Legend of Zelda: Majora's Mask 3D", 'n3ds', null, 2015],
  ['Donkey Kong Country Returns', 'wii', null, 2010],
  ['Donkey Kong Country Returns 3D', 'n3ds', null, 2013],
  ['Earthworm Jim', 'snes', null, 1994],
  ['Earthworm Jim 3D', 'n64', null, 1999],
  ['Okami', 'ps2', null, 2006],
  ['Okami HD', 'ps3', null, 2012],
  ['Dragon Quest XI', 'ps3', null, 2017],
  ['Dragon Quest XI S Definitive Edition', 'ps2', null, 2019],
  // twins: exact, through roman numerals, punctuation, ampersands and apostrophes
  ['Mega Man 2', 'nes', null, 1988],
  ['Mega Man II', 'gb', null, 1991],
  ['Punch-Out!!', 'nes', null, 1987],
  ['Punch-Out!!', 'wii', null, 2009],
  ['Ratchet & Clank', 'ps2', null, 2002],
  ['Ratchet and Clank', 'psp', null, 2003],
  ["Yoshi's Island", 'snes', null, 1995],
  ['Yoshis Island', 'gba', null, 2002],
  ['Street Fighter II: The World Warrior', 'arcade', 'Street Fighter II: The World Warrior', 1991],
  ['Street Fighter II', 'snes', 'Street Fighter II: The World Warrior', 1992],
  // twins: the canonical name wins over the file title
  ['Sonic the Hedgehog', 'md', null, 1991],
  ['Sonic 8-bit', 'sms', 'Sonic the Hedgehog', 1991],
  // the same title on one system is never a twin of itself
  ['Tetris', 'gb', null, 1989],
  ['Tetris', 'gb', null, 1989],
  ['Tetris', 'nes', null, 1989],
  // near names that are not twins
  ['Metroid', 'nes', null, 1986],
  ['Metroid II: Return of Samus', 'gb', null, 1991],
  ['Super Mario Bros.', 'nes', null, 1985],
  ['Super Mario Bros. 3', 'nes', null, 1988],
  ['Mario Kart 64', 'n64', null, 1996],
  ['Mario Kart DS', 'nds', null, 2005],
  // sort keys: articles, accents, digit runs
  ['A Boy and His Blob', 'nes', null, 1989],
  ['An American Tail', 'snes', null, null],
  ['Pokémon Red', 'gb', null, 1996],
  ['Pokemon Blue', 'gb', null, 1996],
  ['Mega Man 10', 'wii', null, 2010],
  ['Zelda II: The Adventure of Link', 'nes', null, 1987],
  ['The Legend of Zelda', 'nes', null, 1986],
  ['Final Fantasy', 'nes', null, 1987],
  ['Final Fantasy VI', 'snes', null, 1994],
  ['Castlevania', 'nes', null, 1986],
  ['Contra', 'nes', null, 1987],
  ['Kirby Super Star', 'snes', null, 1996],
  ['Chrono Trigger', 'snes', null, 1995],
  ['EarthBound', 'snes', null, 1994],
  ['F-Zero', 'snes', null, 1990],
  ['GoldenEye 007', 'n64', null, 1997],
  ['Banjo-Kazooie', 'n64', null, 1998],
  ['Star Fox 64', 'n64', null, 1997],
  ['Pokemon Gold', 'gb', null, null],
  ['Advance Wars', 'gba', null, 2001],
  ['Golden Sun', 'gba', null, 2001],
  ['Metroid Fusion', 'gba', null, 2002],
  ['Phoenix Wright: Ace Attorney', 'nds', null, 2005],
  ['The World Ends with You', 'nds', null, 2007],
  ['Animal Crossing: Wild World', 'nds', null, 2005],
  ['Fire Emblem: Awakening', 'n3ds', null, 2012],
  ['Kid Icarus: Uprising', 'n3ds', null, 2012],
  ['Xenoblade Chronicles', 'wii', null, 2010],
  ['Super Mario Galaxy', 'wii', null, 2007],
  ['Streets of Rage 2', 'md', null, 1992],
  ['Gunstar Heroes', 'md', null, 1993],
  ['Phantasy Star', 'sms', null, 1987],
  ['Alex Kidd in Miracle World', 'sms', null, 1986],
  ['Shadow of the Colossus', 'ps2', null, 2005],
  ['Katamari Damacy', 'ps2', null, 2004],
  ['Persona 4', 'ps2', null, 2008],
  ["Demon's Souls", 'ps3', null, 2009],
  ['Journey', 'ps3', null, 2012],
  ['Patapon', 'psp', null, 2007],
  ['Lumines', 'psp', null, 2004],
  ['Galaga', 'arcade', null, 1981],
  ['Ms. Pac-Man', 'arcade', null, 1982],
  ['Metal Slug', 'arcade', null, 1996],
]

const GENRES = [
  'Platform',
  'Adventure',
  'Role-playing (RPG)',
  'Shooter',
  'Puzzle',
  'Racing',
  'Fighting',
  'Strategy',
  'Sport',
  'Simulator',
  'Arcade',
  'Music',
] as const

const FRANCHISES = [
  'Mario',
  'Zelda',
  'Metroid',
  'Mega Man',
  'Final Fantasy',
  'Pokemon',
  'Sonic',
  'Kirby',
  'Fire Emblem',
  'Street Fighter',
  'Castlevania',
  'Dragon Quest',
] as const
const THEMES = ['Fantasy', 'Science fiction', 'Action', 'Horror', 'Comedy', 'Historical'] as const
const MODES = ['Single player', 'Multiplayer', 'Co-operative', 'Split screen'] as const
const PERSPECTIVES = ['Side view', 'Third person', 'First person', "Bird's eye view"] as const
const REGIONS = ['USA', 'Europe', 'Japan', 'World', 'USA, Europe', 'Japan, USA'] as const

/** Seventy free tags, so the sixty-value cap on a facet is reached. */
const OTHER_TAGS = Array.from({ length: 70 }, (_, i) => `Tag ${String(i + 1).padStart(2, '0')}`)

const pick = <T>(list: readonly T[], i: number): T => {
  const value = list[i % list.length]
  if (value === undefined) throw new Error('empty list')
  return value
}

export function makeGame(seed: Seed, index: number): V1Game {
  const [title, system, igdb, year] = seed
  const id = index + 1
  const franchise = FRANCHISES.find((f) => title.toLowerCase().includes(f.toLowerCase()))
  const tags: V1Tag[] = [
    { tag: pick(OTHER_TAGS, index * 7), kind: 'other' },
    { tag: pick(OTHER_TAGS, index * 13 + 3), kind: 'other' },
    { tag: pick(THEMES, index), kind: 'theme' },
    { tag: pick(MODES, index * 3), kind: 'mode' },
    { tag: pick(PERSPECTIVES, index * 5), kind: 'perspective' },
  ]
  if (franchise) tags.push({ tag: franchise, kind: 'franchise' })
  if (index % 9 === 0) tags.push({ tag: 'Unsorted', kind: 'unknown-kind' })
  return {
    id,
    name: `Synthetic ${String(id).padStart(3, '0')}`,
    title,
    igdb,
    system,
    genres:
      index % 4 === 0 ? [pick(GENRES, index), pick(GENRES, index + 5)] : [pick(GENRES, index)],
    tags,
    region: pick(REGIONS, index),
    year,
    size: 4096 * (index + 1) ** 3,
    rating: index % 6 === 0 ? null : 50 + ((index * 17) % 50),
    votes: index % 6 === 0 ? null : (index * 37) % 400,
    files: index % 5 === 0 ? 3 : 1,
    kind: index % 11 === 0 ? 'folder' : 'file',
    matched: index % 3 !== 0,
    cover: null,
    mtime: 1_700_000_000 + index * 86_400,
  }
}

export function syntheticLibrary(): { systems: Record<string, string>; games: V1Game[] } {
  return { systems: { ...SYSTEMS }, games: SEEDS.map(makeGame) }
}
