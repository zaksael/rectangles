import { describe, expect, it } from 'vitest'
import { buildFixture, fixtureNameFromSearch } from './devFixtures'

describe('buildFixture', () => {
  it('wildcard: a choosing-wildcard turn with legal values and the original roll', () => {
    const state = buildFixture('wildcard')
    expect(state?.game.turn.turnState).toBe('choosingWildcard')
    expect(state?.game.houseRules.wildcard.enabled).toBe(true)
    expect(state?.game.houseRules.wildcard.originalRoll).not.toBeNull()
    expect(state?.game.houseRules.wildcard.legalValues.length).toBeGreaterThan(0)
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
    expect(state?.game.gameOver).toEqual({ reason: 'boardFull', playerId: null, winner: 1 })
    expect(state?.series).toBeNull()
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
