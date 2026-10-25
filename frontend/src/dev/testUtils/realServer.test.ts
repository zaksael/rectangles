import { expect, test } from 'vitest'
import { serverCommand } from './realServer'

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
