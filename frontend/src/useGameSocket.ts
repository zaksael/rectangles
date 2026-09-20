import { useEffect, useRef, useState } from 'react'
import type { ErrorReason, GameWireState, SeriesWireState } from './gameTypes'

interface GameSocketParams {
  protocolVersion: number
  boardSize?: number
}

interface GameState {
  game: GameWireState
  series: SeriesWireState | null
}

interface GameError {
  reason: ErrorReason
  message: string
}

type ConnectionStatus = 'open' | 'closed-intentional' | 'closed-unexpected'

function connectParamsToQuery(params: GameSocketParams): string {
  const query = new URLSearchParams()
  query.set('protocolVersion', String(params.protocolVersion))
  if (params.boardSize !== undefined) {
    query.set('boardSize', String(params.boardSize))
  }
  return query.toString()
}

export function useGameSocket(params: GameSocketParams) {
  const [state, setState] = useState<GameState | null>(null)
  const [error, setError] = useState<GameError | null>(null)
  const [status, setStatus] = useState<ConnectionStatus | undefined>(undefined)
  const socketRef = useRef<WebSocket | null>(null)
  const intentionalCloseRef = useRef(false)

  useEffect(() => {
    intentionalCloseRef.current = false
    const socket = new WebSocket(`/ws?${connectParamsToQuery(params)}`)
    socketRef.current = socket
    socket.addEventListener('open', () => {
      setStatus('open')
    })
    socket.addEventListener('close', () => {
      setStatus(intentionalCloseRef.current ? 'closed-intentional' : 'closed-unexpected')
    })
    socket.addEventListener('message', (event) => {
      const data = JSON.parse(event.data)
      if (data.type === 'state') {
        setState({ game: data.game, series: data.series })
      } else if (data.type === 'error') {
        setError({ reason: data.reason, message: data.message })
      }
    })
    return () => {
      intentionalCloseRef.current = true
      socket.close()
    }
  }, [params.protocolVersion, params.boardSize])

  function disconnect() {
    intentionalCloseRef.current = true
    socketRef.current?.close()
  }

  return { state, error, status, disconnect }
}
