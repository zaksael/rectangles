export class FakeWebSocket {
  static instances: FakeWebSocket[] = []
  url: string
  private listeners: Record<string, ((event: { data: string }) => void)[]> = {}

  constructor(url: string) {
    this.url = url
    FakeWebSocket.instances.push(this)
  }

  close() {
    this.emit('close')
  }

  addEventListener(type: string, listener: (event: { data: string }) => void) {
    this.listeners[type] ??= []
    this.listeners[type].push(listener)
  }

  emit(type: string, data?: unknown) {
    for (const listener of this.listeners[type] ?? []) {
      listener({ data: data === undefined ? '' : JSON.stringify(data) })
    }
  }
}
