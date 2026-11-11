import { expect, test } from 'vitest'
import type { GameWireState, RecentTurn } from './gameTypes'
import { makeGame } from '../dev/fixtures/gameFixtures'
import { recentTurn } from '../dev/testUtils/playingScreenHarness'
import { lastPlacedTopLeft } from './lastPlaced'

const placedAt = (turn: number, playerId: 1 | 2, topLeft: [number, number]): RecentTurn => {
  const entry = recentTurn(turn, playerId, [1, 1], 1)
  return { ...entry, placed: { topLeft, width: 1, height: 1 } }
}
const skipped = (turn: number, playerId: 1 | 2) => recentTurn(turn, playerId, null, 0)

function gameWith(recentTurns: RecentTurn[]): GameWireState {
  const game = makeGame()
  game.turn.recentTurns = recentTurns
  return game
}

test('nothing is marked before any piece is placed', () => {
  expect(lastPlacedTopLeft(gameWith([skipped(1, 1)]))).toBeNull()
})

test('the last piece placed is marked, whoever placed it', () => {
  expect(lastPlacedTopLeft(gameWith([placedAt(1, 1, [0, 0])]))).toEqual([0, 0])
  expect(lastPlacedTopLeft(gameWith([placedAt(1, 1, [0, 0]), placedAt(2, 2, [4, 4])]))).toEqual([4, 4])
})

test('the mark stays on the same piece through the skips after it', () => {
  expect(lastPlacedTopLeft(gameWith([placedAt(1, 1, [0, 0]), skipped(2, 2), skipped(3, 1)]))).toEqual([0, 0])
})

test('a missing game marks nothing', () => {
  expect(lastPlacedTopLeft(null)).toBeNull()
})
