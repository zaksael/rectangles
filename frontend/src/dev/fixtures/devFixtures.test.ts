import { describe, expect, it } from 'vitest'
import { placementReason } from '../../game/placementReason'
import { buildFixture, FIXTURE_ANALYSIS, fixtureNameFromSearch } from './devFixtures'

describe('buildFixture', () => {
  it('wildcard: a choosing-wildcard turn with legal values and the original roll', () => {
    const state = buildFixture('wildcard')
    expect(state?.game.turn.turnState).toBe('choosingWildcard')
    expect(state?.game.houseRules.wildcard.enabled).toBe(true)
    expect(state?.game.houseRules.wildcard.originalRoll).not.toBeNull()
    expect(state?.game.houseRules.wildcard.legalValues.length).toBeGreaterThan(0)
  })

  it('wildcard: the original roll is a double, the only roll that triggers a wildcard', () => {
    const wildcard = buildFixture('wildcard')!.game.houseRules.wildcard
    expect(wildcard.originalRoll![0]).toBe(wildcard.originalRoll![1])
    expect(buildFixture('wildcard')!.game.turn.lastRoll).toEqual(wildcard.originalRoll)
  })

  it('placing: a 2x2 roll to place, and every offered spot is one the placement rules accept', () => {
    const state = buildFixture('placing')!
    expect(state.game.turn.turnState).toBe('choosingPlacement')
    expect(state.game.turn.lastRoll).toEqual([2, 2])
    expect(state.game.turn.currentPlayerId).toBe(1)
    const [offer] = state.game.turn.legalPlacements
    expect(offer).toMatchObject({ width: 2, height: 2 })
    expect(offer!.topLefts.length).toBeGreaterThan(1)
    for (const topLeft of offer!.topLefts) {
      expect(placementReason(state.game, 1, topLeft, [2, 2])).toBeNull()
    }
  })

  it('deadroll: a skipped turn with a roll and no legal placement', () => {
    const state = buildFixture('deadroll')
    expect(state?.game.turn.turnState).toBe('skipped')
    expect(state?.game.turn.lastRoll).not.toBeNull()
    expect(state?.game.turn.legalPlacements).toEqual([])
  })

  it('gameover: a finished game with a reason and a winner, no series', () => {
    const state = buildFixture('gameover')
    expect(state?.game.turn.turnState).toBe('gameOver')
    expect(state?.game.gameOver).toMatchObject({ reason: 'boardFull', playerId: null, winner: 1 })
    expect(state?.game.gameOver.history).toHaveLength(5) // so Replay has something to step through
    expect(state?.series).toBeNull()
  })

  it('gameover: no turn reports more reachable cells than the 10x10 board has empty after it', () => {
    const history = buildFixture('gameover')!.game.gameOver.history!
    let filled = 0
    for (const entry of history) {
      filled += entry.placed ? entry.placed.width * entry.placed.height : 0
      for (const id of ['1', '2'] as const) expect(entry.potential[id].area).toBeLessThanOrEqual(100 - filled)
    }
  })

  it('the canned analysis flags turns that exist in the gameover fixture\'s history', () => {
    const history = buildFixture('gameover')!.game.gameOver.history!
    const turns = FIXTURE_ANALYSIS.status === 'ready' ? FIXTURE_ANALYSIS.turns.map((t) => t.turn) : []

    expect(turns.length).toBeGreaterThan(0)
    expect(turns.every((turn) => history[turn - 1]?.placed)).toBe(true)
  })

  it('the canned analysis suggests the shape that was rolled, in either orientation', () => {
    const history = buildFixture('gameover')!.game.gameOver.history!
    const turns = FIXTURE_ANALYSIS.status === 'ready' ? FIXTURE_ANALYSIS.turns : []
    const shape = (a: number, b: number) => [a, b].sort().join('x')

    expect(turns.map((t) => shape(t.width, t.height))).toEqual(turns.map((t) => shape(...history[t.turn - 1]!.roll)))
  })

  it('series: an incomplete series on a finished round', () => {
    const state = buildFixture('series')
    expect(state?.game.turn.turnState).toBe('gameOver')
    expect(state?.series?.isComplete).toBe(false)
    expect(state?.series?.length).toBe(3)
  })

  it('seriesplay: round two of a best-of-three in progress, awaiting a roll', () => {
    const state = buildFixture('seriesplay')
    expect(state?.game.turn.turnState).toBe('awaitingRoll')
    expect(state?.series?.isComplete).toBe(false)
    expect(state?.series?.gamesPlayed).toBe(1)
    expect(state?.series?.scores).toEqual({ '1': 18, '2': 14 })
  })

  it('series-loserlead: round two won by player 1 while player 2 leads the series', () => {
    const state = buildFixture('series-loserlead')
    expect(state?.game.turn.turnState).toBe('gameOver')
    expect(state?.game.gameOver.winner).toBe(1)
    expect(state?.series?.gamesPlayed).toBe(2)
    expect(state?.series?.scores).toEqual({ '1': 30, '2': 33 })
  })

  it('series-final: a completed series with a winner', () => {
    const state = buildFixture('series-final')
    expect(state?.series?.isComplete).toBe(true)
    expect(state?.series?.winner).toBe(1)
  })

  it('an unknown name builds nothing', () => {
    expect(buildFixture('nope')).toBeNull()
    expect(buildFixture('toString')).toBeNull()
  })
})

describe('fixtureNameFromSearch', () => {
  it('returns a known name', () => {
    expect(fixtureNameFromSearch('?fixture=wildcard')).toBe('wildcard')
  })

  it('returns nothing for an unknown name or with no param', () => {
    expect(fixtureNameFromSearch('?fixture=nope')).toBeNull()
    expect(fixtureNameFromSearch('')).toBeNull()
  })
})
