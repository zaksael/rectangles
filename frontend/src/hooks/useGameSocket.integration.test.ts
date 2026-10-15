import { renderHook, waitFor } from '@testing-library/react'
import { afterAll, beforeAll, expect, test, vi } from 'vitest'
import { WebSocket as NodeWebSocket } from 'ws'
import { startServer } from '../dev/testUtils/realServer'
import { useGameSocket } from './useGameSocket'

// Node's native global WebSocket (undici) throws when dispatching events inside
// the jsdom test environment - its Event class isn't jsdom's. `ws`'s browser-
// compatible client doesn't have that realm mismatch, so use it for this real
// (non-mocked) socket test.
vi.stubGlobal('WebSocket', NodeWebSocket)

let stopServer: () => void
let serverUrl: string

beforeAll(async () => {
  ;({ serverUrl, stop: stopServer } = await startServer())
}, 15_000)

afterAll(() => stopServer())

test(
  'connects to a real running server and receives a state broadcast matching the wire schema',
  async () => {
    const { result } = renderHook(() => useGameSocket({ protocolVersion: 1, serverUrl }))

    await waitFor(() => expect(result.current.state).not.toBeNull())

    const { game, series } = result.current.state!
    expect(typeof game.board.size).toBe('number')
    expect(typeof game.board.skipLimit).toBe('number')
    expect(game.turn.turnState).toBe('awaitingRoll')
    expect(game.players['1']).toBeDefined()
    expect(game.players['2']).toBeDefined()
    expect(series).toBeNull()

    result.current.disconnect()
  },
  15_000,
)
