import { useEffect, useRef, useState } from 'react'
import { Board } from '../components/Board'
import { GameOverOverlay } from './GameOverOverlay'
import { SurrenderConfirmDialog } from './SurrenderConfirmDialog'
import type { ErrorReason, GameAction } from '../gameTypes'
import { ADJACENCY_RULE, placementReason, START_CORNER_RULE } from '../placementReason'
import { useLastPlaced } from '../useLastPlaced'
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

// The key that applies in each of the human's turn states; other states show a blank line.
const KEY_HINT: Partial<Record<string, string>> = {
  awaitingRoll: 'D rolls the dice.',
  choosingPlacement: 'Arrow keys move the piece, Enter places it, R rotates it.',
  skipped: 'S skips this turn.',
}

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
  const placing = humanTurnState === 'choosingPlacement'
  const [confirmingSurrender, setConfirmingSurrender] = useState(false)
  const [dismissedError, setDismissedError] = useState<GameError | null>(null)

  useEffect(() => {
    if (!error) return
    const timer = setTimeout(() => setDismissedError(error), ERROR_TOAST_MS)
    return () => clearTimeout(timer)
  }, [error])

  const sendActionRef = useRef(sendAction)
  sendActionRef.current = sendAction

  const {
    rotate,
    previewTopLeft,
    previewKind,
    coverableCells,
    dims,
    handleCellHover,
    handleCellTap,
    handleBoardFocus,
    handleBoardKeyDown,
  } = usePlacementInput(
    isBotTurn ? null : (state?.game ?? null),
    sendAction,
  )
  const rotateRef = useRef(rotate)
  rotateRef.current = rotate

  const lastPlaced = useLastPlaced(state?.game)

  // The wire clears the roll once a piece is placed; keep it on screen (dimmed) until the next roll.
  const lastRollRef = useRef<{ values: [number, number]; owner: '1' | '2' } | null>(null)
  const roll = state?.game.turn.lastRoll ?? null
  if (roll && state) lastRollRef.current = { values: roll, owner: String(state.game.turn.currentPlayerId) as '1' | '2' }
  const shownRoll = lastRollRef.current

  const currentName = state?.game.players[String(state.game.turn.currentPlayerId) as '1' | '2'].name
  let turnStatus: string | null = null
  if (currentName && turnState !== 'gameOver') {
    if (isBotTurn) turnStatus = `${currentName} is playing…`
    else if (turnState === 'awaitingRoll') turnStatus = `${currentName}: roll`
    else if (turnState === 'choosingPlacement') {
      turnStatus = `${currentName}: place ${dims ? `${dims[0]} wide × ${dims[1]} tall` : 'a rectangle'}`
      const reason =
        previewKind === 'danger' && previewTopLeft && dims && state
          ? placementReason(state.game, state.game.turn.currentPlayerId as 1 | 2, previewTopLeft, dims)
          : null
      const firstMove = state.game.players[String(state.game.turn.currentPlayerId) as '1' | '2'].board.pieces.length === 0
      if (reason) turnStatus += ` — ${reason}`
      else if (previewKind !== 'legal') turnStatus += ` — ${firstMove ? START_CORNER_RULE : ADJACENCY_RULE}`
    }
    else if (turnState === 'skipped') turnStatus = `${currentName}: no legal move, skip`
  }

  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      if (document.querySelector('dialog[open]')) return
      if (event.key === 'd' && humanTurnState === 'awaitingRoll') {
        sendActionRef.current({ type: 'roll' })
      } else if (event.key === 'r' && humanTurnState === 'choosingPlacement') {
        rotateRef.current()
      } else if (event.key === 's' && humanTurnState === 'skipped') {
        sendActionRef.current({ type: 'skip' })
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
          <div className="header">
            {(['1', '2'] as const).map((id) => (
              <div
                key={id}
                className={`player p${id}${state.game.turn.currentPlayerId === Number(id) ? ' current' : ''}`}
                aria-current={state.game.turn.currentPlayerId === Number(id) ? 'true' : undefined}
              >
                <div className="player-id">
                  <span className="dot" aria-hidden="true" />
                  <span className="name">{state.game.players[id].name}</span>
                </div>
                <span className="scoreline">
                  <span className="streak">
                    {state.game.players[id].board.consecutiveSkips}/{state.game.board.skipLimit} skips
                  </span>
                  <span className="score">{state.game.players[id].score.totalScore}</span>
                </span>
              </div>
            ))}
            <div className="toast-anchor" role="status" aria-live="polite">
              {error && error !== dismissedError && <div className="toast">{ERROR_TEXT[error.reason]}</div>}
            </div>
            {turnStatus && (
              <div className="turn-status" data-testid="turn-status" aria-live="polite" aria-atomic="true">
                {turnStatus}
              </div>
            )}
          </div>
          <div className="board-area">
            <Board
              game={state.game}
              previewTopLeft={previewTopLeft}
              previewDims={dims}
              previewKind={previewKind}
              coverableCells={coverableCells}
              lastPlaced={lastPlaced}
              onCellHover={placing ? handleCellHover : undefined}
              onCellTap={placing ? handleCellTap : undefined}
              onKeyDown={placing ? handleBoardKeyDown : undefined}
              onFocus={placing ? handleBoardFocus : undefined}
              describedBy={placing ? 'board-help' : undefined}
            />
            {/* Always rendered (blank when no key applies) so the board doesn't shift vertically. */}
            <p id="board-help" className="board-help">
              {(humanTurnState && KEY_HINT[humanTurnState]) ?? '\u00A0'}
            </p>
          </div>
        </>
      )}
      {state && turnState === 'gameOver' && <GameOverOverlay game={state.game} onNewGame={onNewGame} />}
      {state && confirmingSurrender && (
        <SurrenderConfirmDialog
          opponentName={state.game.players[state.game.turn.currentPlayerId === 1 ? '2' : '1'].name}
          scores={(['1', '2'] as const).map((id) => ({ name: state.game.players[id].name, score: state.game.players[id].score.totalScore }))}
          isSeries={state.series !== null}
          onCancel={() => setConfirmingSurrender(false)}
          onConfirm={() => {
            sendAction({ type: 'surrender' })
            setConfirmingSurrender(false)
          }}
        />
      )}
      <div className="toolbar-actions">
        <div className="toolbar-leading">
          <button className="btn primary" onClick={() => sendAction({ type: 'roll' })} aria-keyshortcuts="d" disabled={isBotTurn || turnState !== 'awaitingRoll'}>
            Roll <kbd aria-hidden="true">D</kbd>
          </button>
          <button className="btn secondary" onClick={rotate} aria-keyshortcuts="r" disabled={isBotTurn || turnState !== 'choosingPlacement'}>
            Rotate <kbd aria-hidden="true">R</kbd>
          </button>
          <button className="btn danger-outline" onClick={() => sendAction({ type: 'skip' })} aria-keyshortcuts="s" disabled={isBotTurn || turnState !== 'skipped'}>
            Skip <kbd aria-hidden="true">S</kbd>
          </button>
        </div>
        {state && shownRoll && (
          <div
            className={`dice p${shownRoll.owner}${roll ? '' : ' stale'}`}
            role="img"
            aria-label={`${state.game.players[shownRoll.owner].name}${roll ? ' rolled' : '’s last roll'} ${shownRoll.values.join(' and ')}`}
          >
            <span className="dot" aria-hidden="true" />
            {shownRoll.values.map((value, i) => (
              <span key={i} className="die">
                {value}
              </span>
            ))}
            {!roll && <span className="dice-label">P{shownRoll.owner} last</span>}
          </div>
        )}
        <div className="toolbar-trailing">
          {state && turnState !== 'gameOver' && (
            <button className="btn secondary quiet" onClick={() => setConfirmingSurrender(true)} disabled={isBotTurn}>
              Surrender
            </button>
          )}
          <button className="btn secondary" onClick={onOpenSettings}>
            Settings
          </button>
        </div>
      </div>
    </div>
  )
}
