import { expect, test } from 'vitest'
import { serverCommand } from './realServer'

test('without RECTANGLES_SERVER_CMD the Python server is started with uv', () => {
  expect(serverCommand({})).toEqual({ command: 'uv', args: ['run', 'python', '-m', 'rectangles.server.app'] })
})

test('RECTANGLES_SERVER_CMD is split on whitespace into the command and its arguments', () => {
  expect(serverCommand({ RECTANGLES_SERVER_CMD: ' server-scala/stage/bin/rectangles-server  --flag  value ' })).toEqual({
    command: 'server-scala/stage/bin/rectangles-server',
    args: ['--flag', 'value'],
  })
})

test('an empty RECTANGLES_SERVER_CMD falls back to the Python server', () => {
  expect(serverCommand({ RECTANGLES_SERVER_CMD: '   ' }).command).toBe('uv')
})
