import { act, renderHook } from '@testing-library/react'
import { afterEach, beforeEach, expect, test, vi } from 'vitest'
import type { GameWireState } from './gameTypes'
import { useGameSocket } from './useGameSocket'

const fakePlayerState = {
  name: 'Player 1',
  board: { startCorner: [0, 0], pieces: [], consecutiveSkips: 0 },
  score: { totalArea: 0, totalScore: 0, potential: { area: 0, prize: { points: 0 } } },
  houseRules: {
    reroll: { used: 0, limit: 0 },
    comebackNudge: { granted: false },
    selfEnclosedPenalty: { cells: 0 },
    prize: { captured: 0 },
    pitfall: { captured: 0 },
    steal: { captured: 0 },
  },
}

const fakeGame: GameWireState = {
  board: { size: 19, skipLimit: 5 },
  turn: { currentPlayerId: 1, turnState: 'awaitingRoll', lastRoll: null, legalPlacements: [] },
  houseRules: {
    wildcard: { enabled: false, originalRoll: null, legalValues: [], editableIndex: null },
    reroll: { enabled: false, canReroll: false },
    comebackNudge: { enabled: false },
    walls: { enabled: false, edges: [] },
    obstacles: { enabled: false, cells: [] },
    prize: { enabled: false, cells: [], points: 0 },
    pitfall: { enabled: false, cells: [], points: 0 },
    steal: { enabled: false, cells: [], points: 0 },
    selfEnclosedPenalty: { enabled: false },
  },
  players: { '1': fakePlayerState, '2': { ...fakePlayerState, name: 'Player 2' } },
  gameOver: { reason: null, playerId: null, winner: null },
}

class FakeWebSocket {
  static instances: FakeWebSocket[] = []
  url: string
  private listeners: Record<string, ((event: { data: string }) => void)[]> = {}

  constructor(url: string) {
    this.url = url
    FakeWebSocket.instances.push(this)
  }

  close() {
    this.emit('close')
  }

  addEventListener(type: string, listener: (event: { data: string }) => void) {
    this.listeners[type] ??= []
    this.listeners[type].push(listener)
  }

  emit(type: string, data?: unknown) {
    for (const listener of this.listeners[type] ?? []) {
      listener({ data: data === undefined ? '' : JSON.stringify(data) })
    }
  }
}

beforeEach(() => {
  FakeWebSocket.instances = []
  vi.stubGlobal('WebSocket', FakeWebSocket)
})

afterEach(() => {
  vi.unstubAllGlobals()
})

test('opens a socket to /ws with the given connect params in the query string', () => {
  renderHook(() => useGameSocket({ protocolVersion: 1, boardSize: 19 }))

  expect(FakeWebSocket.instances).toHaveLength(1)
  expect(FakeWebSocket.instances[0].url).toBe('/ws?protocolVersion=1&boardSize=19')
})

test('exposes the parsed game/series payload from a received state message', () => {
  const { result } = renderHook(() => useGameSocket({ protocolVersion: 1 }))

  act(() => {
    FakeWebSocket.instances[0].emit('message', {
      protocolVersion: 1,
      type: 'state',
      game: fakeGame,
      series: null,
    })
  })

  expect(result.current.state).toEqual({ game: fakeGame, series: null })
})

test('exposes the parsed reason/message from a received error message', () => {
  const { result } = renderHook(() => useGameSocket({ protocolVersion: 1 }))

  act(() => {
    FakeWebSocket.instances[0].emit('message', {
      protocolVersion: 1,
      type: 'error',
      reason: 'illegalPlacement',
      message: 'that cell is already claimed',
    })
  })

  expect(result.current.error).toEqual({
    reason: 'illegalPlacement',
    message: 'that cell is already claimed',
  })
})

test('status becomes "open" once the socket connects', () => {
  const { result } = renderHook(() => useGameSocket({ protocolVersion: 1 }))

  act(() => {
    FakeWebSocket.instances[0].emit('open')
  })

  expect(result.current.status).toBe('open')
})

test('status becomes "closed-intentional" after calling disconnect()', () => {
  const { result } = renderHook(() => useGameSocket({ protocolVersion: 1 }))

  act(() => {
    result.current.disconnect()
  })

  expect(result.current.status).toBe('closed-intentional')
})

test('status becomes "closed-unexpected" when the socket closes without disconnect() having been called', () => {
  const { result } = renderHook(() => useGameSocket({ protocolVersion: 1 }))

  act(() => {
    FakeWebSocket.instances[0].emit('close')
  })

  expect(result.current.status).toBe('closed-unexpected')
})
