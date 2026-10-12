import { act, renderHook } from '@testing-library/react'
import { expect, test, vi } from 'vitest'
import { makeGame } from '../fixtures/gameFixtures'
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

test('coverableCells is the union of every cell any legal placement of the current orientation would cover', () => {
  const game = makeGame({
    board: { size: 5, skipLimit: 5 },
    turn: {
      currentPlayerId: 1,
      turnState: 'choosingPlacement',
      lastRoll: [2, 1],
      legalPlacements: [
        {
          width: 2,
          height: 1,
          topLefts: [
            [0, 0],
            [3, 3],
          ],
        },
      ],
    },
  })

  const { result } = renderHook(() => usePlacementInput(game, vi.fn()))

  expect(result.current.coverableCells).toEqual(
    expect.arrayContaining([
      [0, 0],
      [0, 1],
      [3, 3],
      [3, 4],
    ]),
  )
  expect(result.current.coverableCells).toHaveLength(4)
})

test('coverableCells is empty when there is no active placement', () => {
  const { result } = renderHook(() => usePlacementInput(null, vi.fn()))

  expect(result.current.coverableCells).toEqual([])
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

test('previewKind is "legal" when hovering a legal top-left', () => {
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

  expect(result.current.previewKind).toBe('legal')
})

test('previewKind is "danger" when hovering a top-left with no legal placement there', () => {
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
  act(() => result.current.handleCellHover([4, 4]))

  expect(result.current.previewKind).toBe('danger')
})

test('mouse: tapping a legal cell sends a place action for the computed top-left', () => {
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
  act(() => result.current.handleCellTap([2, 2], 'mouse'))

  expect(sendAction).toHaveBeenCalledWith({ type: 'place', topLeft: [1, 1], width: 2, height: 3 })
})

test('mouse: tapping an illegal cell for the current orientation sends nothing', () => {
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
  act(() => result.current.handleCellTap([4, 4], 'mouse'))

  expect(sendAction).not.toHaveBeenCalled()
})

test('touch: first tap on a legal cell previews it without placing', () => {
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
  act(() => result.current.handleCellTap([2, 2], 'touch'))

  expect(result.current.previewTopLeft).toEqual([1, 1])
  expect(result.current.previewKind).toBe('pending')
  expect(sendAction).not.toHaveBeenCalled()
})

test('touch: the pending preview is shown even over an illegal cell', () => {
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
  act(() => result.current.handleCellTap([4, 4], 'touch'))

  expect(result.current.previewKind).toBe('pending')
})

test('touch: a second tap on the same cell confirms the placement', () => {
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
  act(() => result.current.handleCellTap([2, 2], 'touch'))
  act(() => result.current.handleCellTap([2, 2], 'touch'))

  expect(sendAction).toHaveBeenCalledWith({ type: 'place', topLeft: [1, 1], width: 2, height: 3 })
  expect(result.current.previewTopLeft).toBeNull()
})

test('touch: tapping a different cell relocates the preview instead of placing', () => {
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
  act(() => result.current.handleCellTap([2, 2], 'touch'))
  act(() => result.current.handleCellTap([0, 0], 'touch'))

  expect(sendAction).not.toHaveBeenCalled()
  expect(result.current.previewTopLeft).toEqual([0, 0])
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

// Three legal spots for a 2-wide, 1-tall piece, in row-major order.
const jumpGame = () =>
  makeGame({
    board: { size: 6, skipLimit: 5 },
    turn: {
      currentPlayerId: 1,
      turnState: 'choosingPlacement',
      lastRoll: [2, 1],
      legalPlacements: [{ width: 2, height: 1, topLefts: [[0, 0], [2, 3], [4, 1]] }],
    },
  })
const pressN = (shiftKey = false) => ({ key: shiftKey ? 'N' : 'n', shiftKey, preventDefault: vi.fn() }) as unknown as React.KeyboardEvent

test('keyboard: N jumps the piece to the next legal spot, and it previews as legal', () => {
  const { result } = renderHook(() => usePlacementInput(jumpGame(), vi.fn()))
  act(() => result.current.handleCellHover([0, 1]))
  expect(result.current.previewTopLeft).toEqual([0, 0])

  act(() => result.current.handleBoardKeyDown(pressN()))

  expect(result.current.previewTopLeft).toEqual([2, 3])
  expect(result.current.previewKind).toBe('legal')
})

test('keyboard: N wraps from the last legal spot to the first', () => {
  const { result } = renderHook(() => usePlacementInput(jumpGame(), vi.fn()))
  act(() => result.current.handleCellHover([4, 2]))
  expect(result.current.previewTopLeft).toEqual([4, 1])

  act(() => result.current.handleBoardKeyDown(pressN()))

  expect(result.current.previewTopLeft).toEqual([0, 0])
})

test('keyboard: N with no cursor yet goes to the first legal spot', () => {
  const { result } = renderHook(() => usePlacementInput(jumpGame(), vi.fn()))

  act(() => result.current.handleBoardKeyDown(pressN()))

  expect(result.current.previewTopLeft).toEqual([0, 0])
})

test('keyboard: Shift+N goes back to the previous legal spot, and wraps from the first to the last', () => {
  const { result } = renderHook(() => usePlacementInput(jumpGame(), vi.fn()))
  act(() => result.current.handleCellHover([2, 4]))
  expect(result.current.previewTopLeft).toEqual([2, 3])

  act(() => result.current.handleBoardKeyDown(pressN(true)))
  expect(result.current.previewTopLeft).toEqual([0, 0])

  act(() => result.current.handleBoardKeyDown(pressN(true)))
  expect(result.current.previewTopLeft).toEqual([4, 1])
})

test.each([['ctrlKey'], ['metaKey'], ['altKey']])('keyboard: %s combos are left to the browser (no preventDefault, no move)', (modifier) => {
  const { result } = renderHook(() => usePlacementInput(jumpGame(), vi.fn()))
  act(() => result.current.handleCellHover([0, 1]))

  for (const key of ['n', 'ArrowRight', 'Enter']) {
    const event = { key, shiftKey: false, [modifier]: true, preventDefault: vi.fn() }
    act(() => result.current.handleBoardKeyDown(event as unknown as React.KeyboardEvent))
    expect(event.preventDefault).not.toHaveBeenCalled()
  }
  expect(result.current.previewTopLeft).toEqual([0, 0])
})

test('keyboard: plain N still prevents the browser default', () => {
  const { result } = renderHook(() => usePlacementInput(jumpGame(), vi.fn()))
  const event = pressN()

  act(() => result.current.handleBoardKeyDown(event))

  expect(event.preventDefault).toHaveBeenCalled()
})
