import { act, renderHook } from '@testing-library/react'
import { afterEach, beforeEach, expect, onTestFinished, test, vi } from 'vitest'
import type { GameAction, GameWireState, PlayerState } from '../game/gameTypes'
import { FakeWebSocket } from '../dev/testUtils/FakeWebSocket'
import { useGameSocket } from './useGameSocket'

const fakePlayerState: PlayerState = {
  name: 'Player 1',
  board: { startCorner: [0, 0], pieces: [], consecutiveSkips: 0 },
  score: { totalArea: 0, totalScore: 0, breakdown: { area: 0, prize: 0, pitfall: 0, steal: 0, enclosure: 0 }, potential: { area: 0, prize: { points: 0 } } },
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
  turn: { recentTurns: [], currentPlayerId: 1, turnState: 'awaitingRoll', lastRoll: null, legalPlacements: [] },
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
  gameOver: { history: null, reason: null, playerId: null, winner: null },
}

beforeEach(() => {
  FakeWebSocket.instances = []
  vi.stubGlobal('WebSocket', FakeWebSocket)
  vi.useFakeTimers()
})

afterEach(() => {
  vi.unstubAllGlobals()
  vi.useRealTimers()
})

// An old browser rejects a relative WebSocket URL, so the page's own host is spelled out.
const pageAt = (protocol: string, host: string) => vi.stubGlobal('location', { protocol, host })

test('opens a socket to /ws on the page\'s own host with the given connect params in the query string', () => {
  pageAt('http:', 'game.test:8765')
  renderHook(() => useGameSocket({ protocolVersion: 1, boardSize: 19 }))

  expect(FakeWebSocket.instances).toHaveLength(1)
  expect(FakeWebSocket.instances[0]!.url).toBe('ws://game.test:8765/ws?protocolVersion=1&boardSize=19')
})

test('includes skipLimit/seriesLength/botSeats/botDifficulty/house-rule flags in the connect query when given', () => {
  pageAt('http:', 'game.test:8765')
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

  expect(FakeWebSocket.instances[0]!.url).toBe(
    'ws://game.test:8765/ws?protocolVersion=1&boardSize=19&skipLimit=5&seriesLength=3&botSeats=2&botDifficulty=Greedy' +
      '&wildcardEnabled=false&rerollEnabled=true&wallsEnabled=true&obstaclesEnabled=false' +
      '&prizeEnabled=true&pitfallEnabled=false&stealEnabled=true&selfEnclosedPenaltyEnabled=true' +
      '&comebackNudgeEnabled=false',
  )
})

test('uses wss on an https page', () => {
  pageAt('https:', 'game.test')
  renderHook(() => useGameSocket({ protocolVersion: 1 }))

  expect(FakeWebSocket.instances[0]!.url).toBe('wss://game.test/ws?protocolVersion=1')
})

test('prefixes the socket URL with serverUrl when given', () => {
  renderHook(() => useGameSocket({ protocolVersion: 1, serverUrl: 'ws://127.0.0.1:4000' }))

  expect(FakeWebSocket.instances[0]!.url).toBe('ws://127.0.0.1:4000/ws?protocolVersion=1')
})

test('exposes the parsed game/series payload from a received state message', () => {
  const { result } = renderHook(() => useGameSocket({ protocolVersion: 1 }))

  act(() => {
    FakeWebSocket.instances[0]!.emit('message', {
      protocolVersion: 1,
      type: 'state',
      game: fakeGame,
      series: null,
    })
  })

  expect(result.current.state).toEqual({ game: fakeGame, series: null })
})

test('names the bot seat after its difficulty in the state it exposes, leaving the human seat alone', () => {
  const { result } = renderHook(() => useGameSocket({ protocolVersion: 1, botSeats: 2, botDifficulty: 'Greedy' }))

  act(() => {
    FakeWebSocket.instances[0]!.emit('message', { protocolVersion: 1, type: 'state', game: fakeGame, series: null })
  })

  expect(result.current.state?.game.players['2'].name).toBe('Bot (Greedy)')
  expect(result.current.state?.game.players['1'].name).toBe('Player 1')
})

test('exposes the parsed reason/message from a received error message', () => {
  const { result } = renderHook(() => useGameSocket({ protocolVersion: 1 }))

  act(() => {
    FakeWebSocket.instances[0]!.emit('message', {
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

// FakeWebSocket.emit('message') with no payload delivers an empty string, which is not JSON.
test('a frame that is not JSON surfaces a malformedMessage error and is logged, not thrown out of the listener', () => {
  const log = vi.spyOn(console, 'error').mockImplementation(() => {})
  onTestFinished(() => log.mockRestore())
  const { result } = renderHook(() => useGameSocket({ protocolVersion: 1 }))
  act(() => FakeWebSocket.instances[0]!.emit('open'))

  expect(() => act(() => FakeWebSocket.instances[0]!.emit('message'))).not.toThrow()

  expect(result.current.error).toEqual({ reason: 'malformedMessage', message: 'The server sent a message that could not be read.' })
  expect(log).toHaveBeenCalledTimes(1)
})

test('an unreadable frame while the analysis is loading makes it unavailable', () => {
  vi.spyOn(console, 'error').mockImplementation(() => {})
  onTestFinished(() => void vi.restoreAllMocks())
  const { result } = renderHook(() => useGameSocket({ protocolVersion: 1 }))
  act(() => FakeWebSocket.instances[0]!.emit('open'))
  act(() => result.current.requestAnalysis())

  act(() => FakeWebSocket.instances[0]!.emit('message'))

  expect(result.current.analysis).toEqual({ status: 'unavailable' })
})

test('the next valid state after an unreadable frame still applies, so the board recovers', () => {
  vi.spyOn(console, 'error').mockImplementation(() => {})
  onTestFinished(() => void vi.restoreAllMocks())
  const { result } = renderHook(() => useGameSocket({ protocolVersion: 1 }))
  act(() => FakeWebSocket.instances[0]!.emit('open'))
  act(() => FakeWebSocket.instances[0]!.emit('message'))

  act(() => FakeWebSocket.instances[0]!.emit('message', { protocolVersion: 1, type: 'state', game: fakeGame, series: null }))

  expect(result.current.state).toEqual({ game: fakeGame, series: null })
})

test('status becomes "open" once the socket connects', () => {
  const { result } = renderHook(() => useGameSocket({ protocolVersion: 1 }))

  act(() => {
    FakeWebSocket.instances[0]!.emit('open')
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
    FakeWebSocket.instances[0]!.emit('open')
    FakeWebSocket.instances[0]!.emit('close')
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
    FakeWebSocket.instances[0]!.emit('close')
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
  act(() => FakeWebSocket.instances[0]!.emit('open'))

  act(() => {
    result.current.sendAction(action)
  })

  expect(FakeWebSocket.instances[0]!.sent).toEqual([expected])
})

test('applies a single state message immediately, with no delay', () => {
  const { result } = renderHook(() => useGameSocket({ protocolVersion: 1 }))

  act(() => {
    FakeWebSocket.instances[0]!.emit('message', {
      protocolVersion: 1,
      type: 'state',
      game: fakeGame,
      series: null,
    })
  })

  expect(result.current.state).toEqual({ game: fakeGame, series: null })
})

test('a second state message arriving before the delay elapses is not applied yet', () => {
  const secondGame: GameWireState = { ...fakeGame, turn: { ...fakeGame.turn, lastRoll: [3, 4] } }
  const { result } = renderHook(() => useGameSocket({ protocolVersion: 1 }))

  act(() => {
    FakeWebSocket.instances[0]!.emit('message', { protocolVersion: 1, type: 'state', game: fakeGame, series: null })
    FakeWebSocket.instances[0]!.emit('message', {
      protocolVersion: 1,
      type: 'state',
      game: secondGame,
      series: null,
    })
  })

  expect(result.current.state).toEqual({ game: fakeGame, series: null })
})

test('the queued second state message applies once the pacing delay elapses', () => {
  const secondGame: GameWireState = { ...fakeGame, turn: { ...fakeGame.turn, lastRoll: [3, 4] } }
  const { result } = renderHook(() => useGameSocket({ protocolVersion: 1 }))

  act(() => {
    FakeWebSocket.instances[0]!.emit('message', { protocolVersion: 1, type: 'state', game: fakeGame, series: null })
    FakeWebSocket.instances[0]!.emit('message', {
      protocolVersion: 1,
      type: 'state',
      game: secondGame,
      series: null,
    })
    vi.advanceTimersByTime(500)
  })

  expect(result.current.state).toEqual({ game: secondGame, series: null })
})

test('a state arriving after the pacing queue went idle shows at once', () => {
  const secondGame: GameWireState = { ...fakeGame, turn: { ...fakeGame.turn, lastRoll: [3, 4] } }
  const { result } = renderHook(() => useGameSocket({ protocolVersion: 1 }))

  act(() => {
    FakeWebSocket.instances[0]!.emit('message', { protocolVersion: 1, type: 'state', game: fakeGame, series: null })
    vi.advanceTimersByTime(500)
    FakeWebSocket.instances[0]!.emit('message', { protocolVersion: 1, type: 'state', game: secondGame, series: null })
  })

  expect(result.current.state).toEqual({ game: secondGame, series: null })
})

test('reconnecting while a state waits on the pacing delay drops it, and the new game shows at once', () => {
  const secondGame: GameWireState = { ...fakeGame, turn: { ...fakeGame.turn, lastRoll: [3, 4] } }
  const newGame: GameWireState = { ...fakeGame, turn: { ...fakeGame.turn, lastRoll: [1, 1] } }
  const { result, rerender } = renderHook((connectionId: number) => useGameSocket({ protocolVersion: 1, connectionId }), { initialProps: 1 })

  act(() => {
    FakeWebSocket.instances[0]!.emit('message', { protocolVersion: 1, type: 'state', game: fakeGame, series: null })
    FakeWebSocket.instances[0]!.emit('message', { protocolVersion: 1, type: 'state', game: secondGame, series: null })
  })
  rerender(2)
  act(() => {
    FakeWebSocket.instances[1]!.emit('message', { protocolVersion: 1, type: 'state', game: newGame, series: null })
  })

  expect(result.current.state).toEqual({ game: newGame, series: null })
  act(() => {
    vi.advanceTimersByTime(1000)
  })
  expect(result.current.state).toEqual({ game: newGame, series: null })
})

test('three back-to-back state messages surface one at a time, in order, not collapsed to the last', () => {
  const secondGame: GameWireState = { ...fakeGame, turn: { ...fakeGame.turn, lastRoll: [3, 4] } }
  const thirdGame: GameWireState = { ...fakeGame, turn: { ...fakeGame.turn, lastRoll: [1, 1] } }
  const { result } = renderHook(() => useGameSocket({ protocolVersion: 1 }))
  const seen: (GameWireState | undefined)[] = []

  act(() => {
    for (const game of [fakeGame, secondGame, thirdGame]) {
      FakeWebSocket.instances[0]!.emit('message', { protocolVersion: 1, type: 'state', game, series: null })
    }
  })
  seen.push(result.current.state?.game)

  act(() => {
    vi.advanceTimersByTime(500)
  })
  seen.push(result.current.state?.game)

  act(() => {
    vi.advanceTimersByTime(500)
  })
  seen.push(result.current.state?.game)

  expect(seen).toEqual([fakeGame, secondGame, thirdGame])
})

test('bumping connectionId opens a fresh socket even with otherwise unchanged params', () => {
  const { rerender } = renderHook((params) => useGameSocket(params), {
    initialProps: { protocolVersion: 1, connectionId: 0 },
  })

  expect(FakeWebSocket.instances).toHaveLength(1)

  rerender({ protocolVersion: 1, connectionId: 1 })

  expect(FakeWebSocket.instances).toHaveLength(2)
})

test('a fresh connection clears the previous game state and error', () => {
  const { result, rerender } = renderHook((params) => useGameSocket(params), {
    initialProps: { protocolVersion: 1, connectionId: 0 },
  })
  act(() => {
    FakeWebSocket.instances[0]!.emit('message', { protocolVersion: 1, type: 'state', game: fakeGame, series: null })
    FakeWebSocket.instances[0]!.emit('message', {
      protocolVersion: 1,
      type: 'error',
      reason: 'illegalPlacement',
      message: 'x',
    })
  })
  expect(result.current.state).not.toBeNull()
  expect(result.current.error).not.toBeNull()

  rerender({ protocolVersion: 1, connectionId: 1 })

  expect(result.current.state).toBeNull()
  expect(result.current.error).toBeNull()
})

const analysisTurns = [{ turn: 3, axis: 'prize', chosen: 0, best: 10, topLeft: [0, 0], width: 4, height: 1 }]
const analysisMessage = { protocolVersion: 1, type: 'analysis', turns: analysisTurns }
const stateMessage = (game: GameWireState = fakeGame) => ({ type: 'state', game, series: null })

test('a fresh connection starts with no status again, until its socket opens', () => {
  const { result, rerender } = renderHook((params) => useGameSocket(params), {
    initialProps: { protocolVersion: 1, connectionId: 0 },
  })
  act(() => FakeWebSocket.instances[0]!.emit('open'))
  expect(result.current.status).toBe('open')

  rerender({ protocolVersion: 1, connectionId: 1 })
  expect(result.current.status).toBeUndefined()

  act(() => FakeWebSocket.instances[1]!.emit('open'))
  expect(result.current.status).toBe('open')
})

test('turning the connection off keeps the last game state and reads closed, so the board can still be shown', async () => {
  const { result, rerender } = renderHook((params) => useGameSocket(params), {
    initialProps: { protocolVersion: 1, connectionId: 0, enabled: true },
  })
  act(() => {
    FakeWebSocket.instances[0]!.emit('open')
    FakeWebSocket.instances[0]!.emit('message', { protocolVersion: 1, type: 'state', game: fakeGame, series: null })
  })

  rerender({ protocolVersion: 1, connectionId: 0, enabled: false })
  await act(async () => {}) // the socket reports its close a tick after close()

  expect(result.current.state).not.toBeNull()
  expect(result.current.status).toBe('closed-intentional')
})

test('turning the connection back on with the same params starts with no status, not the closed one', async () => {
  const { result, rerender } = renderHook((params) => useGameSocket(params), {
    initialProps: { protocolVersion: 1, connectionId: 0, enabled: true },
  })
  act(() => FakeWebSocket.instances[0]!.emit('open'))
  rerender({ protocolVersion: 1, connectionId: 0, enabled: false })
  await act(async () => {})
  expect(result.current.status).toBe('closed-intentional')

  rerender({ protocolVersion: 1, connectionId: 0, enabled: true })

  expect(result.current.status).toBeUndefined()
})

test('a fresh connection drops an analysis held from the last game', () => {
  const { result, rerender } = renderHook((params) => useGameSocket(params), {
    initialProps: { protocolVersion: 1, connectionId: 0 },
  })
  act(() => {
    FakeWebSocket.instances[0]!.emit('open')
    FakeWebSocket.instances[0]!.emit('message', { protocolVersion: 1, type: 'state', game: { ...fakeGame, gameOver: { reason: 'boardFull', playerId: null, winner: 1, history: [] } }, series: null })
    result.current.requestAnalysis()
    FakeWebSocket.instances[0]!.emit('message', analysisMessage)
  })
  expect(result.current.analysis?.status).toBe('ready')

  rerender({ protocolVersion: 1, connectionId: 1 })

  expect(result.current.analysis).toBeNull()
})


test('requestAnalysis sends the request and the analysis reads loading', () => {
  const { result } = renderHook(() => useGameSocket({ protocolVersion: 1 }))
  act(() => FakeWebSocket.instances[0]!.emit('open'))
  expect(result.current.analysis).toBeNull()

  act(() => result.current.requestAnalysis())

  expect(FakeWebSocket.instances[0]!.sent).toEqual([{ protocolVersion: 1, type: 'requestAnalysis' }])
  expect(result.current.analysis).toEqual({ status: 'loading' })
})

test('an analysis message makes the analysis ready with its turns', () => {
  const { result } = renderHook(() => useGameSocket({ protocolVersion: 1 }))
  act(() => FakeWebSocket.instances[0]!.emit('open'))
  act(() => result.current.requestAnalysis())

  act(() => FakeWebSocket.instances[0]!.emit('message', analysisMessage))

  expect(result.current.analysis).toEqual({ status: 'ready', turns: analysisTurns })
})

test('an error reply while the analysis is loading makes it unavailable', () => {
  const { result } = renderHook(() => useGameSocket({ protocolVersion: 1 }))
  act(() => FakeWebSocket.instances[0]!.emit('open'))
  act(() => result.current.requestAnalysis())

  act(() => FakeWebSocket.instances[0]!.emit('message', { type: 'error', reason: 'invalidAction', message: 'the game is not over' }))

  expect(result.current.analysis).toEqual({ status: 'unavailable' })
})

test('the socket closing while the analysis is loading makes it unavailable', () => {
  const { result } = renderHook(() => useGameSocket({ protocolVersion: 1 }))
  act(() => FakeWebSocket.instances[0]!.emit('open'))
  act(() => result.current.requestAnalysis())

  act(() => FakeWebSocket.instances[0]!.emit('close'))

  expect(result.current.analysis).toEqual({ status: 'unavailable' })
})

const unavailableAfterError = () => {
  const hook = renderHook(() => useGameSocket({ protocolVersion: 1 }))
  act(() => FakeWebSocket.instances[0]!.emit('open'))
  act(() => hook.result.current.requestAnalysis())
  act(() => FakeWebSocket.instances[0]!.emit('message', { type: 'error', reason: 'invalidAction', message: 'the game is not over' }))
  expect(hook.result.current.analysis).toEqual({ status: 'unavailable' })
  return hook.result
}

test('asking again once the analysis is unavailable sends a new request', () => {
  const result = unavailableAfterError()

  act(() => result.current.requestAnalysis())

  expect(FakeWebSocket.instances[0]!.sent).toEqual([
    { protocolVersion: 1, type: 'requestAnalysis' },
    { protocolVersion: 1, type: 'requestAnalysis' },
  ])
  expect(result.current.analysis).toEqual({ status: 'loading' })
})

test('the retried request can succeed', () => {
  const result = unavailableAfterError()
  act(() => result.current.requestAnalysis())

  act(() => FakeWebSocket.instances[0]!.emit('message', analysisMessage))

  expect(result.current.analysis).toEqual({ status: 'ready', turns: analysisTurns })
})

test('asking again while a request is still loading sends nothing', () => {
  const { result } = renderHook(() => useGameSocket({ protocolVersion: 1 }))
  act(() => FakeWebSocket.instances[0]!.emit('open'))
  act(() => result.current.requestAnalysis())

  act(() => result.current.requestAnalysis())

  expect(FakeWebSocket.instances[0]!.sent).toHaveLength(1)
})

test('asking again once the analysis is ready sends nothing', () => {
  const { result } = renderHook(() => useGameSocket({ protocolVersion: 1 }))
  act(() => FakeWebSocket.instances[0]!.emit('open'))
  act(() => result.current.requestAnalysis())
  act(() => FakeWebSocket.instances[0]!.emit('message', analysisMessage))

  act(() => result.current.requestAnalysis())

  expect(FakeWebSocket.instances[0]!.sent).toHaveLength(1)
})

test('the next game starting clears the previous round\'s analysis', () => {
  const { result } = renderHook(() => useGameSocket({ protocolVersion: 1 }))
  act(() => FakeWebSocket.instances[0]!.emit('open'))
  act(() => result.current.requestAnalysis())
  act(() => FakeWebSocket.instances[0]!.emit('message', analysisMessage))

  act(() => FakeWebSocket.instances[0]!.emit('message', stateMessage()))

  expect(result.current.analysis).toBeNull()
})

test('a game-over state keeps the analysis', () => {
  const { result } = renderHook(() => useGameSocket({ protocolVersion: 1 }))
  act(() => FakeWebSocket.instances[0]!.emit('open'))
  act(() => result.current.requestAnalysis())
  act(() => FakeWebSocket.instances[0]!.emit('message', analysisMessage))
  const over = { ...fakeGame, gameOver: { ...fakeGame.gameOver, reason: 'surrender', history: [] } } as GameWireState

  act(() => FakeWebSocket.instances[0]!.emit('message', stateMessage(over)))

  expect(result.current.analysis).toEqual({ status: 'ready', turns: analysisTurns })
})
