import { useEffect, useRef, useState } from 'react'
import type { ErrorReason, GameAction, GameWireState, SeriesWireState } from './gameTypes'

interface GameSocketParams {
  protocolVersion: number
  boardSize?: number
  skipLimit?: number
  seriesLength?: number
  botSeats?: number
  botDifficulty?: string
  wildcardEnabled?: boolean
  rerollEnabled?: boolean
  wallsEnabled?: boolean
  obstaclesEnabled?: boolean
  prizeEnabled?: boolean
  pitfallEnabled?: boolean
  stealEnabled?: boolean
  selfEnclosedPenaltyEnabled?: boolean
  comebackNudgeEnabled?: boolean
  serverUrl?: string
  enabled?: boolean
  connectionId?: number
}

const QUERY_PARAM_KEYS = [
  'protocolVersion',
  'boardSize',
  'skipLimit',
  'seriesLength',
  'botSeats',
  'botDifficulty',
  'wildcardEnabled',
  'rerollEnabled',
  'wallsEnabled',
  'obstaclesEnabled',
  'prizeEnabled',
  'pitfallEnabled',
  'stealEnabled',
  'selfEnclosedPenaltyEnabled',
  'comebackNudgeEnabled',
] as const satisfies readonly (keyof GameSocketParams)[]

export interface GameState {
  game: GameWireState
  series: SeriesWireState | null
}

export interface GameError {
  reason: ErrorReason
  message: string
}

type ConnectionStatus = 'open' | 'closed-intentional' | 'closed-unexpected' | 'connect-failed'

const STATE_PACING_DELAY_MS = 500

function connectParamsToQuery(params: GameSocketParams): string {
  const query = new URLSearchParams()
  for (const key of QUERY_PARAM_KEYS) {
    const value = params[key]
    if (value !== undefined) {
      query.set(key, String(value))
    }
  }
  return query.toString()
}

export function useGameSocket(params: GameSocketParams) {
  const [state, setState] = useState<GameState | null>(null)
  const [error, setError] = useState<GameError | null>(null)
  const [status, setStatus] = useState<ConnectionStatus | undefined>(undefined)
  const socketRef = useRef<WebSocket | null>(null)
  const intentionalCloseRef = useRef(false)
  const hasOpenedRef = useRef(false)
  const stateQueueRef = useRef<GameState[]>([])
  const drainTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  // A primitive dependency: the effect reconnects exactly when a connect param changes.
  const query = connectParamsToQuery(params)

  useEffect(() => {
    if (params.enabled === false) {
      return
    }
    intentionalCloseRef.current = false
    hasOpenedRef.current = false
    setStatus(undefined)
    setState(null)
    setError(null)
    stateQueueRef.current = []
    if (drainTimeoutRef.current !== null) {
      clearTimeout(drainTimeoutRef.current)
      drainTimeoutRef.current = null
    }

    function drainNext() {
      const next = stateQueueRef.current.shift()
      if (next === undefined) {
        drainTimeoutRef.current = null
        return
      }
      setState(next)
      drainTimeoutRef.current = setTimeout(drainNext, STATE_PACING_DELAY_MS)
    }
    const socket = new WebSocket(`${params.serverUrl ?? ''}/ws?${query}`)
    socketRef.current = socket
    socket.addEventListener('open', () => {
      hasOpenedRef.current = true
      setStatus('open')
    })
    socket.addEventListener('close', () => {
      if (intentionalCloseRef.current) {
        setStatus('closed-intentional')
      } else if (hasOpenedRef.current) {
        setStatus('closed-unexpected')
      } else {
        setStatus('connect-failed')
      }
    })
    socket.addEventListener('message', (event) => {
      const data = JSON.parse(event.data)
      if (data.type === 'state') {
        stateQueueRef.current.push({ game: data.game, series: data.series })
        if (drainTimeoutRef.current === null) {
          drainNext()
        }
      } else if (data.type === 'error') {
        setError({ reason: data.reason, message: data.message })
      }
    })
    return () => {
      intentionalCloseRef.current = true
      if (drainTimeoutRef.current !== null) {
        clearTimeout(drainTimeoutRef.current)
        drainTimeoutRef.current = null
      }
      socket.close()
    }
  }, [query, params.serverUrl, params.enabled, params.connectionId])

  function disconnect() {
    intentionalCloseRef.current = true
    // The socket's `close` event fires asynchronously; until it does, status would still read 'open'.
    setStatus('closed-intentional')
    socketRef.current?.close()
  }

  function sendAction(action: GameAction) {
    socketRef.current?.send(JSON.stringify({ protocolVersion: params.protocolVersion, ...action }))
  }

  return { state, error, status, disconnect, sendAction }
}
