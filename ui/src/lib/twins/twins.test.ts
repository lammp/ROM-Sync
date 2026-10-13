import { describe, expect, it } from 'vitest'
import { buildTwins, twinKey, twinKeyLoose, twinWords, type Twinnable } from './twins'

let next = 0
const g = (title: string, system: string, igdb_name: string | null = null): Twinnable => ({
  id: ++next,
  system,
  igdb_name,
  title,
  name: `${title}.rom`,
})

describe('twin keys', () => {
  it('reads the canonical name first, then the title', () => {
    expect(twinKey(g('Zelda 64', 'n64', "The Legend of Zelda: Majora's Mask"))).toBe(
      'legendofzeldamajorasmask',
    )
    expect(twinKey(g('Tetris', 'gb'))).toBe('tetris')
  })

  it('reads & as and, numerals as digits, and drops articles and "part"', () => {
    expect(twinWords(g('Final Fantasy VII & Part II', 'ps1'))).toEqual([
      'final',
      'fantasy',
      '7',
      'and',
      '2',
    ])
  })

  it('undoes stylised letters', () => {
    expect(twinKey(g('Punch-Out!!', 'nes'))).toBe('punchoutii')
    expect(twinKey(g('Ca$h Gr@b', 'nes'))).toBe('cashgrab')
  })

  it('drops trailing release forms only from the loose key, keeping one word', () => {
    const remaster = g('Shadow of the Colossus HD Remastered', 'ps3')
    expect([twinKey(remaster), twinKeyLoose(remaster)]).toEqual([
      'shadowofcolossushdremastered',
      'shadowofcolossus',
    ])
    expect(twinKeyLoose(g('Deluxe', 'nes'))).toBe('deluxe')
  })
})

describe('buildTwins', () => {
  it('pairs the same game across systems, never on its own system', () => {
    const a = g('Tetris', 'gb')
    const b = g('Tetris', 'nes')
    const c = g('Tetris', 'gb')
    const twins = buildTwins([a, b, c])
    expect(twins.get(a.id)?.map((t) => [t.game.id, t.loose])).toEqual([[b.id, false]])
    expect(twins.get(b.id)?.map((t) => t.game.id)).toEqual([a.id, c.id])
  })

  it('marks a pair that meets only after the strip as loose', () => {
    const jim = g('Earthworm Jim', 'md')
    const jim3d = g('Earthworm Jim 3D', 'n64')
    expect(buildTwins([jim, jim3d]).get(jim.id)).toEqual([{ game: jim3d, loose: true }])
  })

  it('leaves out a game with no twin, and one with no name', () => {
    const lone = g('Rez', 'ps2')
    const blank = { id: ++next, system: 'nes', igdb_name: null, title: '', name: '' }
    expect(buildTwins([lone, blank, { ...blank, id: ++next, system: 'snes' }]).size).toBe(0)
  })
})
