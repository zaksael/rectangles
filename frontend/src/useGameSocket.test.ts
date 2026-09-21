import { act, renderHook } from '@testing-library/react'
import { afterEach, beforeEach, expect, test, vi } from 'vitest'
import type { GameAction, GameWireState } from './gameTypes'
import { FakeWebSocket } from './testUtils/FakeWebSocket'
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

test('includes skipLimit/seriesLength/botSeats/botDifficulty/house-rule flags in the connect query when given', () => {
  renderHook(() =>
    useGameSocket({
      protocolVersion: 1,
      boardSize: 19,
      skipLimit: 5,
      seriesLength: 3,
      botSeats: 2,
      botDifficulty: 'Greedy',
      wildcardEnabled: false,
      rerollEnabled: true,
      wallsEnabled: true,
      obstaclesEnabled: false,
      prizeEnabled: true,
      pitfallEnabled: false,
      stealEnabled: true,
      selfEnclosedPenaltyEnabled: true,
      comebackNudgeEnabled: false,
    }),
  )

  expect(FakeWebSocket.instances[0].url).toBe(
    '/ws?protocolVersion=1&boardSize=19&skipLimit=5&seriesLength=3&botSeats=2&botDifficulty=Greedy' +
      '&wildcardEnabled=false&rerollEnabled=true&wallsEnabled=true&obstaclesEnabled=false' +
      '&prizeEnabled=true&pitfallEnabled=false&stealEnabled=true&selfEnclosedPenaltyEnabled=true' +
      '&comebackNudgeEnabled=false',
  )
})

test('prefixes the socket URL with serverUrl when given', () => {
  renderHook(() => useGameSocket({ protocolVersion: 1, serverUrl: 'ws://127.0.0.1:4000' }))

  expect(FakeWebSocket.instances[0].url).toBe('ws://127.0.0.1:4000/ws?protocolVersion=1')
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

test('status becomes "closed-unexpected" when an open socket closes without disconnect() having been called', () => {
  const { result } = renderHook(() => useGameSocket({ protocolVersion: 1 }))

  act(() => {
    FakeWebSocket.instances[0].emit('open')
    FakeWebSocket.instances[0].emit('close')
  })

  expect(result.current.status).toBe('closed-unexpected')
})

test('does not open a socket when enabled is false', () => {
  renderHook(() => useGameSocket({ protocolVersion: 1, enabled: false }))

  expect(FakeWebSocket.instances).toHaveLength(0)
})

test('status becomes "connect-failed" when the socket closes before ever opening', () => {
  const { result } = renderHook(() => useGameSocket({ protocolVersion: 1 }))

  act(() => {
    FakeWebSocket.instances[0].emit('close')
  })

  expect(result.current.status).toBe('connect-failed')
})

test.each<[GameAction, unknown]>([
  [{ type: 'roll' }, { protocolVersion: 1, type: 'roll' }],
  [{ type: 'skip' }, { protocolVersion: 1, type: 'skip' }],
  [{ type: 'reroll' }, { protocolVersion: 1, type: 'reroll' }],
  [{ type: 'surrender' }, { protocolVersion: 1, type: 'surrender' }],
  [{ type: 'chooseWildcard', value: 4 }, { protocolVersion: 1, type: 'chooseWildcard', value: 4 }],
  [
    { type: 'place', topLeft: [2, 3], width: 4, height: 5 },
    { protocolVersion: 1, type: 'place', topLeft: [2, 3], width: 4, height: 5 },
  ],
])('sendAction(%o) sends the matching wire message with protocolVersion', (action, expected) => {
  const { result } = renderHook(() => useGameSocket({ protocolVersion: 1 }))

  act(() => {
    result.current.sendAction(action)
  })

  expect(FakeWebSocket.instances[0].sent).toEqual([expected])
})

test('bumping connectionId opens a fresh socket even with otherwise unchanged params', () => {
  const { rerender } = renderHook((params) => useGameSocket(params), {
    initialProps: { protocolVersion: 1, connectionId: 0 },
  })

  expect(FakeWebSocket.instances).toHaveLength(1)

  rerender({ protocolVersion: 1, connectionId: 1 })

  expect(FakeWebSocket.instances).toHaveLength(2)
})
