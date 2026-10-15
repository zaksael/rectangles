import { expect, test, vi } from 'vitest'
import { FakeWebSocket } from './FakeWebSocket'

test('close() reports the close event on a later tick, as a real socket does after its handshake', async () => {
  const socket = new FakeWebSocket('/ws')
  const onClose = vi.fn()
  socket.addEventListener('close', onClose)

  socket.close()
  expect(onClose).not.toHaveBeenCalled()

  await Promise.resolve()
  expect(onClose).toHaveBeenCalledTimes(1)
})

test('send() throws while the socket is still connecting, and works once it has opened', () => {
  const socket = new FakeWebSocket('/ws')

  expect(() => socket.send(JSON.stringify({ type: 'roll' }))).toThrow(/InvalidStateError|CONNECTING/)

  socket.emit('open')
  socket.send(JSON.stringify({ type: 'roll' }))
  expect(socket.sent).toEqual([{ type: 'roll' }])
})
