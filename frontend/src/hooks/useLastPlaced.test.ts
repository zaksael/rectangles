import { renderHook } from '@testing-library/react'
import { expect, test } from 'vitest'
import type { GameWireState, RecentTurn } from '../game/gameTypes'
import { makeGame } from '../dev/fixtures/gameFixtures'
import { recentTurn } from '../dev/testUtils/playingScreenHarness'
import { useLastPlaced } from './useLastPlaced'

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
  const { result } = renderHook(() => useLastPlaced(gameWith([skipped(1, 1)])))

  expect(result.current).toBeNull()
})

test('the piece that just landed is marked, whoever placed it', () => {
  const { result, rerender } = renderHook(({ game }) => useLastPlaced(game), { initialProps: { game: gameWith([]) } })

  rerender({ game: gameWith([placedAt(1, 1, [0, 0])]) })
  expect(result.current).toEqual([0, 0])

  rerender({ game: gameWith([placedAt(1, 1, [0, 0]), placedAt(2, 2, [4, 4])]) })
  expect(result.current).toEqual([4, 4])
})

test('the mark stays on the same piece through the skips after it', () => {
  const { result } = renderHook(() => useLastPlaced(gameWith([placedAt(1, 1, [0, 0]), skipped(2, 2), skipped(3, 1)])))

  expect(result.current).toEqual([0, 0])
})

test('a game already holding pieces at the first render marks the last one placed', () => {
  const { result } = renderHook(() => useLastPlaced(gameWith([placedAt(1, 1, [0, 0]), placedAt(2, 2, [4, 4])])))

  expect(result.current).toEqual([4, 4])
})

test('a missing game marks nothing', () => {
  const { result } = renderHook(() => useLastPlaced(null))

  expect(result.current).toBeNull()
})
