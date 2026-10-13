import { renderHook } from '@testing-library/react'
import { expect, test } from 'vitest'
import type { GameWireState, PieceState } from '../game/gameTypes'
import { makeGame } from '../dev/fixtures/gameFixtures'
import { useLastPlaced } from './useLastPlaced'

const piece = (owner: number, row: number, col: number): PieceState => ({ topLeft: [row, col], width: 1, height: 1, owner })

function gameWith(one: PieceState[], two: PieceState[]): GameWireState {
  const game = makeGame()
  game.players['1'].board.pieces = one
  game.players['2'].board.pieces = two
  return game
}

test('nothing is marked before any piece is placed', () => {
  const { result } = renderHook(({ game }) => useLastPlaced(game), { initialProps: { game: gameWith([], []) } })

  expect(result.current).toBeNull()
})

test('the piece that just landed is marked, whoever placed it', () => {
  const { result, rerender } = renderHook(({ game }) => useLastPlaced(game), { initialProps: { game: gameWith([], []) } })

  rerender({ game: gameWith([piece(1, 0, 0)], []) })
  expect(result.current).toEqual([0, 0])

  rerender({ game: gameWith([piece(1, 0, 0)], [piece(2, 4, 4)]) })
  expect(result.current).toEqual([4, 4])
})

test('the mark stays on the same piece through a state with no new piece (a skip)', () => {
  const { result, rerender } = renderHook(({ game }) => useLastPlaced(game), { initialProps: { game: gameWith([], []) } })
  rerender({ game: gameWith([piece(1, 0, 0)], []) })

  rerender({ game: gameWith([piece(1, 0, 0)], []) })
  rerender({ game: gameWith([piece(1, 0, 0)], []) })

  expect(result.current).toEqual([0, 0])
})

test('a game already holding pieces at the first render has no mark until a piece lands', () => {
  const { result, rerender } = renderHook(({ game }) => useLastPlaced(game), { initialProps: { game: gameWith([piece(1, 0, 0)], [piece(2, 4, 4)]) } })
  expect(result.current).toBeNull()

  rerender({ game: gameWith([piece(1, 0, 0), piece(1, 2, 2)], [piece(2, 4, 4)]) })
  expect(result.current).toEqual([2, 2])
})

test('a missing game keeps the mark and the next game is compared with the last one seen', () => {
  const { result, rerender } = renderHook(({ game }: { game: GameWireState | null }) => useLastPlaced(game), {
    initialProps: { game: gameWith([], []) as GameWireState | null },
  })
  rerender({ game: gameWith([piece(1, 0, 0)], []) })

  rerender({ game: null })
  expect(result.current).toEqual([0, 0])

  rerender({ game: gameWith([piece(1, 0, 0)], [piece(2, 4, 4)]) })
  expect(result.current).toEqual([4, 4])
})
