import { expect, test } from 'vitest'
import { makeHistoryEntry } from '../dev/fixtures/gameFixtures'
import { rolledArea } from './luck'

test("sums each player's own rolls as width times height and ignores the other player's moves", () => {
  const history = [
    makeHistoryEntry({ playerId: 1, roll: [3, 4] }),
    makeHistoryEntry({ playerId: 2, roll: [2, 5] }),
    makeHistoryEntry({ playerId: 1, roll: [6, 1] }),
  ]

  expect([rolledArea(history, 1), rolledArea(history, 2)]).toEqual([18, 10])
})

test('a wildcard roll counts the dice the player was dealt, not the number they edited it to', () => {
  const history = [makeHistoryEntry({ playerId: 1, roll: [4, 6], wildcardOriginalRoll: [4, 4] })]

  expect(rolledArea(history, 1)).toBe(16)
})

test('a skipped turn still counts as a roll the player was dealt', () => {
  const history = [makeHistoryEntry({ playerId: 2, roll: [5, 5], placed: null })]

  expect(rolledArea(history, 2)).toBe(25)
})

test('an empty history is zero rolled area', () => {
  expect(rolledArea([], 1)).toBe(0)
})
