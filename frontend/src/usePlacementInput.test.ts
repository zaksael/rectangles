import { act, renderHook } from '@testing-library/react'
import { expect, test, vi } from 'vitest'
import { makeGame } from './testUtils/gameFixtures'
import { usePlacementInput } from './usePlacementInput'

test('returns inert values when there is no game yet', () => {
  const { result } = renderHook(() => usePlacementInput(null, vi.fn()))

  expect(result.current.dims).toBeNull()
  expect(result.current.previewTopLeft).toBeNull()
})

test('picks the (a, b) orientation when it is legal for the roll', () => {
  const game = makeGame({
    turn: {
      currentPlayerId: 1,
      turnState: 'choosingPlacement',
      lastRoll: [2, 3],
      legalPlacements: [{ width: 2, height: 3, topLefts: [[0, 0]] }],
    },
  })

  const { result } = renderHook(() => usePlacementInput(game, vi.fn()))

  expect(result.current.dims).toEqual([2, 3])
})

test('rotate swaps width and height', () => {
  const game = makeGame({
    turn: {
      currentPlayerId: 1,
      turnState: 'choosingPlacement',
      lastRoll: [2, 3],
      legalPlacements: [
        { width: 2, height: 3, topLefts: [[0, 0]] },
        { width: 3, height: 2, topLefts: [[0, 0]] },
      ],
    },
  })

  const { result } = renderHook(() => usePlacementInput(game, vi.fn()))

  act(() => result.current.rotate())

  expect(result.current.dims).toEqual([3, 2])
})

test('hovering a cell previews the piece centered on it, clamped to the board', () => {
  const game = makeGame({
    board: { size: 5, skipLimit: 5 },
    turn: {
      currentPlayerId: 1,
      turnState: 'choosingPlacement',
      lastRoll: [2, 3],
      legalPlacements: [{ width: 2, height: 3, topLefts: [[1, 1]] }],
    },
  })

  const { result } = renderHook(() => usePlacementInput(game, vi.fn()))

  act(() => result.current.handleCellHover([2, 2]))
  expect(result.current.previewTopLeft).toEqual([1, 1])

  act(() => result.current.handleCellHover([0, 0]))
  expect(result.current.previewTopLeft).toEqual([0, 0])
})

test('clicking a legal cell sends a place action for the computed top-left', () => {
  const game = makeGame({
    board: { size: 5, skipLimit: 5 },
    turn: {
      currentPlayerId: 1,
      turnState: 'choosingPlacement',
      lastRoll: [2, 3],
      legalPlacements: [{ width: 2, height: 3, topLefts: [[1, 1]] }],
    },
  })
  const sendAction = vi.fn()

  const { result } = renderHook(() => usePlacementInput(game, sendAction))
  act(() => result.current.handleCellClick([2, 2]))

  expect(sendAction).toHaveBeenCalledWith({ type: 'place', topLeft: [1, 1], width: 2, height: 3 })
})

test('clicking an illegal cell for the current orientation sends nothing', () => {
  const game = makeGame({
    board: { size: 5, skipLimit: 5 },
    turn: {
      currentPlayerId: 1,
      turnState: 'choosingPlacement',
      lastRoll: [2, 3],
      legalPlacements: [{ width: 2, height: 3, topLefts: [[1, 1]] }],
    },
  })
  const sendAction = vi.fn()

  const { result } = renderHook(() => usePlacementInput(game, sendAction))
  act(() => result.current.handleCellClick([4, 4]))

  expect(sendAction).not.toHaveBeenCalled()
})

test('falls back to the (b, a) orientation when only that one is legal', () => {
  const game = makeGame({
    turn: {
      currentPlayerId: 1,
      turnState: 'choosingPlacement',
      lastRoll: [2, 3],
      legalPlacements: [{ width: 3, height: 2, topLefts: [[0, 0]] }],
    },
  })

  const { result } = renderHook(() => usePlacementInput(game, vi.fn()))

  expect(result.current.dims).toEqual([3, 2])
})
