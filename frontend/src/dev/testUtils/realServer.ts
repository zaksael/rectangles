import { type ChildProcess, spawn } from 'node:child_process'
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

// Under a loaded machine the JVM can take a while to bind its port.
const READY_TIMEOUT_MS = 30_000

function waitForServerReady(serverUrl: string, timeoutMs: number, exited: Promise<never>): Promise<void> {
  const deadline = Date.now() + timeoutMs
  let settled = false // the server exited, or became ready: stop polling
  const ready = new Promise<void>((resolve, reject) => {
    function attempt() {
      const socket = new NodeWebSocket(`${serverUrl}/ws?protocolVersion=1`)
      socket.addEventListener('open', () => {
        socket.close()
        resolve()
      })
      socket.addEventListener('error', () => {
        if (settled) return
        if (Date.now() > deadline) {
          reject(new Error(`server at ${serverUrl} did not become ready in time`))
          return
        }
        setTimeout(attempt, 200)
      })
    }
    attempt()
  })
  return Promise.race([ready, exited]).finally(() => {
    settled = true
  })
}

// Rejects when the process ends (ignored once the server was ready); keeps the tail of its output so the error says why.
function watchExit(serverProcess: ChildProcess): Promise<never> {
  let tail = ''
  const collect = (chunk: Buffer) => {
    tail = (tail + chunk.toString()).slice(-4000)
  }
  serverProcess.stdout?.on('data', collect)
  serverProcess.stderr?.on('data', collect)
  const exited = new Promise<never>((_, reject) => {
    serverProcess.on('error', (err) => reject(new Error(`could not start the server: ${err.message}`)))
    serverProcess.on('exit', (code, signal) => reject(new Error(`server exited with code ${code ?? signal} before it was ready:\n${tail}`)))
  })
  exited.catch(() => {})
  return exited
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
  const [command, ...args] = (env['RECTANGLES_SERVER_CMD'] ?? '').trim().split(/\s+/)
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
  const exited = watchExit(serverProcess)
  try {
    await waitForServerReady(serverUrl, READY_TIMEOUT_MS, exited)
  } catch (err) {
    serverProcess.kill()
    throw err
  }
  return { serverUrl, stop: () => serverProcess.kill() }
}
