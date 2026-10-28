import { chmodSync, mkdtempSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import path from 'node:path'
import { afterEach, expect, test } from 'vitest'
import { serverCommand, startServer } from './realServer'

afterEach(() => {
  delete process.env.RECTANGLES_SERVER_CMD
})

test('without RECTANGLES_SERVER_CMD the staged Scala launcher is started', () => {
  expect(serverCommand({})).toEqual({ command: expect.stringMatching(/server-scala\/target\/stage\/bin\/rectangles-server$/), args: [] })
})

test('RECTANGLES_SERVER_CMD is split on whitespace into the command and its arguments', () => {
  expect(serverCommand({ RECTANGLES_SERVER_CMD: ' server-scala/stage/bin/rectangles-server  --flag  value ' })).toEqual({
    command: 'server-scala/stage/bin/rectangles-server',
    args: ['--flag', 'value'],
  })
})

test('an empty RECTANGLES_SERVER_CMD falls back to the staged launcher', () => {
  expect(serverCommand({ RECTANGLES_SERVER_CMD: '   ' })).toEqual(serverCommand({}))
})

test('a server that exits before it is ready rejects at once, naming the exit and what it printed', async () => {
  const script = path.join(mkdtempSync(path.join(tmpdir(), 'fake-server-')), 'server.sh')
  writeFileSync(script, '#!/bin/sh\necho boom-from-server >&2\nexit 3\n')
  chmodSync(script, 0o755)
  process.env.RECTANGLES_SERVER_CMD = script
  const started = Date.now()
  await expect(startServer()).rejects.toThrow(/exited with code 3[\s\S]*boom-from-server/)
  expect(Date.now() - started).toBeLessThan(5_000)
})
