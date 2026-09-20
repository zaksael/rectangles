import { type ChildProcess, spawn } from 'node:child_process'
import { createServer } from 'node:net'
import path from 'node:path'
import { renderHook, waitFor } from '@testing-library/react'
import { afterAll, beforeAll, expect, test, vi } from 'vitest'
import { WebSocket as NodeWebSocket } from 'ws'
import { useGameSocket } from './useGameSocket'

// Node's native global WebSocket (undici) throws when dispatching events inside
// the jsdom test environment - its Event class isn't jsdom's. `ws`'s browser-
// compatible client doesn't have that realm mismatch, so use it for this real
// (non-mocked) socket test.
vi.stubGlobal('WebSocket', NodeWebSocket)

const REPO_ROOT = path.resolve(__dirname, '../..')

function pickFreePort(): Promise<number> {
  return new Promise((resolve, reject) => {
    const server = createServer()
    server.listen(0, () => {
      const address = server.address()
      if (address === null || typeof address === 'string') {
        reject(new Error('could not determine a free port'))
        return
      }
      const { port } = address
      server.close(() => resolve(port))
    })
  })
}

function waitForServerReady(serverUrl: string, timeoutMs: number): Promise<void> {
  const deadline = Date.now() + timeoutMs
  return new Promise((resolve, reject) => {
    function attempt() {
      const socket = new WebSocket(`${serverUrl}/ws?protocolVersion=1`)
      socket.addEventListener('open', () => {
        socket.close()
        resolve()
      })
      socket.addEventListener('error', () => {
        if (Date.now() > deadline) {
          reject(new Error(`server at ${serverUrl} did not become ready in time`))
          return
        }
        setTimeout(attempt, 200)
      })
    }
    attempt()
  })
}

let serverProcess: ChildProcess
let serverUrl: string

beforeAll(async () => {
  const port = await pickFreePort()
  serverUrl = `ws://127.0.0.1:${port}`
  serverProcess = spawn('uv', ['run', 'python', '-m', 'rectangles.server.app'], {
    cwd: REPO_ROOT,
    env: { ...process.env, RECTANGLES_SERVER_PORT: String(port) },
  })
  await waitForServerReady(serverUrl, 10_000)
}, 15_000)

afterAll(() => {
  serverProcess.kill()
})

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
