import { useEffect, useRef, useState } from 'react'
import { Board } from '../components/Board'
import { GameOverOverlay } from './GameOverOverlay'
import { SurrenderConfirmDialog } from './SurrenderConfirmDialog'
import type { ErrorReason, GameAction } from '../gameTypes'
import { usePlacementInput } from '../usePlacementInput'
import type { GameError, GameState } from '../useGameSocket'
import './PlayingScreen.css'

interface PlayingScreenProps {
  state: GameState | null
  error: GameError | null
  sendAction: (action: GameAction) => void
  onOpenSettings: () => void
  onNewGame: () => void
  botSeat?: number
}

const ERROR_TOAST_MS = 4000

const ERROR_TEXT: Record<ErrorReason, string> = {
  illegalPlacement: 'That piece can’t go there — try another spot.',
  invalidAction: 'You can’t do that right now — finish your current step.',
  protocolVersionMismatch: 'This game is out of date — reload the page.',
  illegalWildcardValue: 'That number can’t be placed — pick another.',
  malformedMessage: 'Something went wrong — try again.',
}

export function PlayingScreen({ state, error, sendAction, onOpenSettings, onNewGame, botSeat }: PlayingScreenProps) {
  const turnState = state?.game.turn.turnState
  // The bot acts on its own turns; the human's controls stay inert until it hands back.
  const isBotTurn = botSeat !== undefined && state?.game.turn.currentPlayerId === botSeat
  const humanTurnState = isBotTurn ? undefined : turnState
  const [confirmingSurrender, setConfirmingSurrender] = useState(false)
  const [dismissedError, setDismissedError] = useState<GameError | null>(null)

  useEffect(() => {
    if (!error) return
    const timer = setTimeout(() => setDismissedError(error), ERROR_TOAST_MS)
    return () => clearTimeout(timer)
  }, [error])

  const sendActionRef = useRef(sendAction)
  sendActionRef.current = sendAction

  const { rotate, previewTopLeft, previewKind, coverableCells, dims, handleCellHover, handleCellTap } = usePlacementInput(
    isBotTurn ? null : (state?.game ?? null),
    sendAction,
  )
  const rotateRef = useRef(rotate)
  rotateRef.current = rotate

  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      if (document.querySelector('dialog[open]')) return
      if (event.key === 'd' && humanTurnState === 'awaitingRoll') {
        sendActionRef.current({ type: 'roll' })
      } else if (event.key === 'r' && humanTurnState === 'choosingPlacement') {
        rotateRef.current()
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [humanTurnState])

  return (
    <div className="frame">
      <h1 className="visually-hidden">Playing</h1>
      {state && (
        <>
          {turnState !== 'gameOver' && (
            <div className="visually-hidden turn-announcer" aria-live="polite">
              {state.game.players[String(state.game.turn.currentPlayerId) as '1' | '2'].name}’s turn
            </div>
          )}
          <div className="header">
            {(['1', '2'] as const).map((id) => (
              <div
                key={id}
                className={`player p${id}${state.game.turn.currentPlayerId === Number(id) ? ' current' : ''}`}
                aria-current={state.game.turn.currentPlayerId === Number(id) ? 'true' : undefined}
              >
                <span className="dot" aria-hidden="true" />
                <span className="name">{state.game.players[id].name}</span>
                <span className="scoreline">
                  <span className="score">{state.game.players[id].score.totalScore}</span>
                  <span className="streak">
                    {state.game.players[id].board.consecutiveSkips}/{state.game.board.skipLimit} skips
                  </span>
                </span>
              </div>
            ))}
          </div>
          <div className="board-area">
            <div className="toast-anchor" role="status" aria-live="polite">
              {error && error !== dismissedError && <div className="toast">{ERROR_TEXT[error.reason]}</div>}
            </div>
            <Board
              game={state.game}
              previewTopLeft={previewTopLeft}
              previewDims={dims}
              previewKind={previewKind}
              coverableCells={coverableCells}
              onCellHover={humanTurnState === 'choosingPlacement' ? handleCellHover : undefined}
              onCellTap={humanTurnState === 'choosingPlacement' ? handleCellTap : undefined}
            />
          </div>
        </>
      )}
      {state && turnState === 'gameOver' && <GameOverOverlay game={state.game} onNewGame={onNewGame} />}
      {state && confirmingSurrender && (
        <SurrenderConfirmDialog
          opponentName={state.game.players[state.game.turn.currentPlayerId === 1 ? '2' : '1'].name}
          isSeries={state.series !== null}
          onCancel={() => setConfirmingSurrender(false)}
          onConfirm={() => {
            sendAction({ type: 'surrender' })
            setConfirmingSurrender(false)
          }}
        />
      )}
      <div className="toolbar-actions">
        {turnState === 'awaitingRoll' && (
          <button className="btn primary" onClick={() => sendAction({ type: 'roll' })} disabled={isBotTurn}>
            Roll
          </button>
        )}
        {state && turnState !== 'awaitingRoll' && state.game.turn.lastRoll && (
          <div className="dice" role="img" aria-label={`Rolled ${state.game.turn.lastRoll.join(' and ')}`}>
            {state.game.turn.lastRoll.map((value, i) => (
              <span key={i} className="die">
                {value}
              </span>
            ))}
          </div>
        )}
        {turnState === 'choosingPlacement' && (
          <button className="btn secondary" onClick={rotate} disabled={isBotTurn}>
            Rotate
          </button>
        )}
        {turnState === 'skipped' && (
          <button className="btn danger-outline" onClick={() => sendAction({ type: 'skip' })} disabled={isBotTurn}>
            Skip
          </button>
        )}
        <div className="toolbar-trailing">
          {state && turnState !== 'gameOver' && (
            <button className="btn secondary" onClick={() => setConfirmingSurrender(true)} disabled={isBotTurn}>
              Surrender
            </button>
          )}
          <button className="btn secondary pause" onClick={onOpenSettings}>
            Pause
          </button>
        </div>
      </div>
    </div>
  )
}
