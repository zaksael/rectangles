import { spawn } from 'node:child_process'
import { createServer } from 'node:net'
import path from 'node:path'
import { WebSocket as NodeWebSocket } from 'ws'

const REPO_ROOT = path.resolve(__dirname, '../../../..')

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
      const socket = new NodeWebSocket(`${serverUrl}/ws?protocolVersion=1`)
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

// Starts the real Python server on a free port for a test file; call `stop` in afterAll.
export async function startServer(): Promise<{ serverUrl: string; stop: () => void }> {
  const port = await pickFreePort()
  const serverUrl = `ws://127.0.0.1:${port}`
  const serverProcess = spawn('uv', ['run', 'python', '-m', 'rectangles.server.app'], {
    cwd: REPO_ROOT,
    env: { ...process.env, RECTANGLES_SERVER_PORT: String(port) },
  })
  await waitForServerReady(serverUrl, 10_000)
  return { serverUrl, stop: () => serverProcess.kill() }
}
