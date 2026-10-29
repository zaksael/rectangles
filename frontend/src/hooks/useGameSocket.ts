import { useEffect, useRef, useState } from 'react'
import type { Analysis, ErrorReason, GameAction, GameWireState, SeriesWireState } from '../game/gameTypes'

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
  // The wait between two queued states; not a connect param, so changing it never reconnects.
  pacingDelayMs?: number
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

const DEFAULT_PACING_DELAY_MS = 500

export const botName = (difficulty?: string) => `Bot (${difficulty})`

const isObject = (value: unknown): boolean => typeof value === 'object' && value !== null

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
  // Each status report names the connection it belongs to, so a late close from the socket before this one cannot read as this one's.
  const [statusEntry, setStatusEntry] = useState<{ connection: string | null; value: ConnectionStatus } | undefined>(undefined)
  const [analysis, setAnalysisState] = useState<Analysis | null>(null)
  // The latest analysis, readable from handlers that outlive a render (the socket's listeners, requestAnalysis).
  const analysisRef = useRef<Analysis | null>(null)
  const socketRef = useRef<WebSocket | null>(null)
  const intentionalCloseRef = useRef(false)
  const hasOpenedRef = useRef(false)
  const stateQueueRef = useRef<GameState[]>([])
  const drainTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  // Read when each wait starts, so a change applies from the next one without a new connection.
  const pacingDelayRef = useRef(DEFAULT_PACING_DELAY_MS)
  useEffect(() => {
    pacingDelayRef.current = params.pacingDelayMs ?? DEFAULT_PACING_DELAY_MS
  }, [params.pacingDelayMs])
  function setAnalysis(next: Analysis | null) {
    analysisRef.current = next
    setAnalysisState(next)
  }
  // A request that is still waiting when it fails or the connection drops has no answer coming.
  function failPendingAnalysis() {
    if (analysisRef.current?.status === 'loading') setAnalysis({ status: 'unavailable' })
  }
  // A primitive dependency: the effect reconnects exactly when a connect param changes.
  const query = connectParamsToQuery(params)

  // Names the connection the params ask for (null while turned off, which keeps the last game on show). A new one starts from a blank
  // slate: the old game, error, status and analysis belong to the connection before. Set during render, so no stale frame shows.
  const connection = params.enabled === false ? null : `${params.connectionId}|${params.serverUrl ?? ''}|${query}`
  const status = connection === null || statusEntry?.connection === connection ? statusEntry?.value : undefined
  const [seenConnection, setSeenConnection] = useState(connection)
  if (connection !== seenConnection) {
    setSeenConnection(connection)
    if (connection !== null) {
      setStatusEntry(undefined)
      setState(null)
      setError(null)
      setAnalysisState(null)
    }
  }

  useEffect(() => {
    if (params.enabled === false) {
      return
    }
    intentionalCloseRef.current = false
    hasOpenedRef.current = false
    const setStatus = (value: ConnectionStatus) => setStatusEntry({ connection, value })
    analysisRef.current = null
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
      // A state with no history is a game still in play: any analysis held belongs to the round before.
      if (!next.game.gameOver.history) setAnalysis(null)
      drainTimeoutRef.current = setTimeout(drainNext, pacingDelayRef.current)
    }
    // Spelled out, not '/ws': browsers before 2024 reject a relative WebSocket URL with a SyntaxError.
    const base = params.serverUrl ?? `${window.location.protocol === 'https:' ? 'wss' : 'ws'}://${window.location.host}`
    const socket = new WebSocket(`${base}/ws?${query}`)
    socketRef.current = socket
    socket.addEventListener('open', () => {
      hasOpenedRef.current = true
      setStatus('open')
    })
    socket.addEventListener('close', () => {
      failPendingAnalysis()
      if (intentionalCloseRef.current) {
        setStatus('closed-intentional')
      } else if (hasOpenedRef.current) {
        setStatus('closed-unexpected')
      } else {
        setStatus('connect-failed')
      }
    })
    socket.addEventListener('message', (event) => {
      // States are full snapshots, so the next valid one heals the board; meanwhile say so instead of freezing silently.
      const reject = (cause: unknown) => {
        console.error('Unreadable message from the server', cause)
        setError({ reason: 'malformedMessage', message: 'The server sent a message that could not be read.' })
        failPendingAnalysis()
      }
      let data
      try {
        data = JSON.parse(event.data)
      } catch (cause) {
        reject(cause)
        return
      }
      if (!isObject(data)) {
        reject(data)
        return
      }
      // The server always sends it; a frame without one is not a version clash, a different number is.
      if (data.protocolVersion !== undefined && data.protocolVersion !== params.protocolVersion) {
        setError({ reason: 'protocolVersionMismatch', message: 'The server speaks a different protocol version.' })
        failPendingAnalysis()
        return
      }
      if (data.type === 'state') {
        if (!isObject(data.game) || !isObject(data.game.players) || !isObject(data.game.turn) || !isObject(data.game.gameOver) || (data.series !== null && !isObject(data.series))) {
          reject(data)
          return
        }
        const botSeat = params.botSeats
        const game: GameWireState =
          botSeat === undefined
            ? data.game
            : { ...data.game, players: { ...data.game.players, [botSeat]: { ...data.game.players[botSeat], name: botName(params.botDifficulty) } } }
        stateQueueRef.current.push({ game, series: data.series })
        if (drainTimeoutRef.current === null) {
          drainNext()
        }
      } else if (data.type === 'analysis') {
        setAnalysis({ status: 'ready', turns: data.turns })
      } else if (data.type === 'error') {
        setError({ reason: data.reason, message: data.message })
        failPendingAnalysis()
      } else {
        reject(data)
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
  }, [connection, query, params.serverUrl, params.enabled, params.connectionId, params.botSeats, params.botDifficulty, params.protocolVersion])

  function disconnect() {
    intentionalCloseRef.current = true
    // The socket's `close` event fires asynchronously; until it does, status would still read 'open'.
    setStatusEntry({ connection, value: 'closed-intentional' })
    socketRef.current?.close()
  }

  function sendAction(action: GameAction) {
    socketRef.current?.send(JSON.stringify({ protocolVersion: params.protocolVersion, ...action }))
  }

  // Asks once: a request already out, or an answer already held, is not repeated; one that failed may be asked again.
  function requestAnalysis() {
    if (analysisRef.current !== null && analysisRef.current.status !== 'unavailable') return
    setAnalysis({ status: 'loading' })
    sendAction({ type: 'requestAnalysis' })
  }

  return { state, error, status, analysis, requestAnalysis, disconnect, sendAction }
}
