import { spawn } from 'node:child_process'
import { existsSync } from 'node:fs'
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

export interface ServerCommand {
  command: string
  args: string[]
}

const STAGED_LAUNCHER = path.join(REPO_ROOT, 'server-scala/target/stage/bin/rectangles-server')
const SCALA_SERVER: ServerCommand = { command: STAGED_LAUNCHER, args: [] }

// RECTANGLES_SERVER_CMD replaces the staged Scala launcher (`sbt server/stage` in server-scala/ builds it). It is split on
// whitespace and run without a shell, so `stop` kills the server itself, not a wrapper around it.
export function serverCommand(env: Record<string, string | undefined>): ServerCommand {
  const [command, ...args] = (env.RECTANGLES_SERVER_CMD ?? '').trim().split(/\s+/)
  return command ? { command, args } : SCALA_SERVER
}

// Starts the real server (the staged Scala launcher, or the command in RECTANGLES_SERVER_CMD) on a free port for a test file; call `stop` in afterAll.
export async function startServer(): Promise<{ serverUrl: string; stop: () => void }> {
  const port = await pickFreePort()
  const serverUrl = `ws://127.0.0.1:${port}`
  const { command, args } = serverCommand(process.env)
  if (command === STAGED_LAUNCHER && !existsSync(command)) throw new Error('no staged server: run `sbt server/stage` in server-scala/ first')
  const serverProcess = spawn(command, args, {
    cwd: REPO_ROOT,
    env: { ...process.env, RECTANGLES_SERVER_PORT: String(port) },
  })
  await waitForServerReady(serverUrl, 10_000)
  return { serverUrl, stop: () => serverProcess.kill() }
}
