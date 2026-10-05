import { useEffect, useRef, useState } from 'react'
import { Board } from '../components/Board'
import { GameOverBar, GameOverOverlay } from './GameOverOverlay'
import type { ErrorReason, GameAction } from '../gameTypes'
import { ADJACENCY_RULE, placementReason, START_CORNER_RULE } from '../placementReason'
import { useLastPlaced } from '../useLastPlaced'
import { usePlacementInput } from '../usePlacementInput'
import type { GameError, GameState } from '../useGameSocket'
import { noBreak } from '../noBreak'
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
// A Comeback grant is easy to miss, so its notice stays twice as long as an error toast.
const COMEBACK_TOAST_MS = 8000

// The key that applies in each of the human's turn states; other states show a blank line.
const KEY_HINT: Partial<Record<string, string>> = {
  choosingPlacement: 'Arrows move, N next legal spot, Enter places, R rotates',
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
  const [dismissedError, setDismissedError] = useState<GameError | null>(null)

  useEffect(() => {
    if (!error) return
    const timer = setTimeout(() => setDismissedError(error), ERROR_TOAST_MS)
    return () => clearTimeout(timer)
  }, [error])

  // The wire only carries the current `granted` flag, so a grant is spotted as false -> true between states.
  const [comebackNotice, setComebackNotice] = useState<string | null>(null)
  // After the game ends, the player can put the result away to look at the final board.
  const [resultHidden, setResultHidden] = useState(false)
  const grantedRef = useRef<Record<'1' | '2', boolean> | null>(null)
  useEffect(() => {
    if (!state) return
    const now = { '1': state.game.players['1'].houseRules.comebackNudge.granted, '2': state.game.players['2'].houseRules.comebackNudge.granted }
    const before = grantedRef.current ?? now
    grantedRef.current = now
    const newly = (['1', '2'] as const).find((id) => now[id] && !before[id])
    if (newly) setComebackNotice(`Comeback! ${noBreak(state.game.players[newly].name)} gets +1 reroll`)
  }, [state])

  useEffect(() => {
    if (!comebackNotice) return
    const timer = setTimeout(() => setComebackNotice(null), COMEBACK_TOAST_MS)
    return () => clearTimeout(timer)
  }, [comebackNotice])

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

  const rerollEnabled = state?.game.houseRules.reroll.enabled ?? false
  const canReroll = state?.game.houseRules.reroll.canReroll ?? false
  const rerollUsable = canReroll && ['choosingPlacement', 'skipped', 'choosingWildcard'].includes(humanTurnState ?? '')

  const lastPlaced = useLastPlaced(state?.game)

  // The wire clears the roll once a piece is placed; keep it on screen (dimmed) until the next roll.
  const lastRollRef = useRef<{ values: [number, number]; owner: '1' | '2' } | null>(null)
  const roll = state?.game.turn.lastRoll ?? null
  const wildcard = state?.game.houseRules.wildcard
  const pickIndex = humanTurnState === 'choosingWildcard' && roll ? (wildcard?.editableIndex ?? null) : null

  const pills = wildcard && (
    <div key="pills" role="group" aria-label="Wildcard value" className="wildcard-pills">
      {[1, 2, 3, 4, 5, 6].map((value) => (
        <button
          key={value}
          className="pill"
          disabled={!wildcard.legalValues.includes(value)}
          onClick={() => sendAction({ type: 'chooseWildcard', value })}
        >
          {value}
        </button>
      ))}
    </div>
  )
  const fixedDie = pickIndex !== null && roll && (
    <span key="die" className="die" data-testid="wildcard-fixed-die" role="img" aria-label={`Fixed die ${roll[1 - pickIndex]}`}>
      {roll[1 - pickIndex]}
    </span>
  )
  if (roll && state) lastRollRef.current = { values: roll, owner: String(state.game.turn.currentPlayerId) as '1' | '2' }
  const shownRoll = lastRollRef.current

  // In board view the result bar takes the header's place, so the player cells are not rendered.
  const showResultBar = turnState === 'gameOver' && resultHidden
  // Once the game is over nobody is to move, so the header stops marking a player.
  const currentId = turnState === 'gameOver' ? null : state?.game.turn.currentPlayerId
  const currentName = state && noBreak(state.game.players[String(state.game.turn.currentPlayerId) as '1' | '2'].name)
  let turnStatus: string | null = null
  if (currentName && turnState !== 'gameOver') {
    if (isBotTurn) turnStatus = `${currentName} is playing…`
    else if (turnState === 'awaitingRoll') turnStatus = `${currentName}: roll (D)`
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
    else if (turnState === 'choosingWildcard') turnStatus = `${currentName}: wildcard roll — pick the other die’s value${canReroll ? ', or reroll (E)' : ''}`
    else if (turnState === 'skipped') {
      turnStatus = canReroll ? `${currentName}: no legal move — skip (S), or reroll (E)` : `${currentName}: no legal move, skip (S)`
      const { skipLimit } = state.game.board
      const nextSkip = state.game.players[String(state.game.turn.currentPlayerId) as '1' | '2'].board.consecutiveSkips + 1
      turnStatus += nextSkip >= skipLimit ? ` · skip ${skipLimit} of ${skipLimit} ends the game` : ` · skip ${nextSkip} of ${skipLimit}`
    }
  }

  const keyHint = humanTurnState && KEY_HINT[humanTurnState]
  const boardHint = keyHint ? (rerollUsable ? `${keyHint}, E rerolls` : keyHint) : '\u00A0'

  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      if (document.querySelector('dialog[open]')) return
      if (event.ctrlKey || event.metaKey || event.altKey) return
      const key = event.key.toLowerCase()
      if (key === 'd' && humanTurnState === 'awaitingRoll') {
        sendActionRef.current({ type: 'roll' })
      } else if (key === 'r' && humanTurnState === 'choosingPlacement') {
        rotateRef.current()
      } else if (key === 's' && humanTurnState === 'skipped') {
        sendActionRef.current({ type: 'skip' })
      } else if (key === 'e' && rerollUsable) {
        sendActionRef.current({ type: 'reroll' })
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [humanTurnState, rerollUsable])

  return (
    <div className={wildcard?.enabled ? 'frame reserves-picker' : 'frame'}>
      <h1 className="visually-hidden">Playing</h1>
      {state && (
        <>
          <div className="header">
            {!showResultBar && (['1', '2'] as const).map((id) => (
              <div
                key={id}
                className={`player p${id}${currentId === Number(id) ? ' current' : ''}`}
                aria-current={currentId === Number(id) ? 'true' : undefined}
              >
                <div className="player-id">
                  <span className="dot" aria-hidden="true" />
                  <span className="name">{state.game.players[id].name}</span>
                </div>
                <span className="scoreline">
                  <span className={state.game.players[id].board.consecutiveSkips + 1 >= state.game.board.skipLimit ? 'streak last-skip' : 'streak'}>
                    {state.game.players[id].board.consecutiveSkips}/{state.game.board.skipLimit} skips
                    {rerollEnabled &&
                      `, ${state.game.players[id].houseRules.reroll.limit - state.game.players[id].houseRules.reroll.used}/${state.game.players[id].houseRules.reroll.limit} rerolls`}
                  </span>
                  <span className="score">
                    {state.game.players[id].score.totalScore}
                    <span className="visually-hidden"> points</span>
                  </span>
                </span>
              </div>
            ))}
            <div className="toast-anchor" role="status" aria-live="polite">
              {error && error !== dismissedError && <div className="toast">{ERROR_TEXT[error.reason]}</div>}
              {comebackNotice && <div className="toast">{comebackNotice}</div>}
            </div>
            {showResultBar && (
              <GameOverBar game={state.game} onViewResult={() => setResultHidden(false)} onNewGame={onNewGame} />
            )}
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
              {boardHint}
            </p>
          </div>
        </>
      )}
      {state && turnState === 'gameOver' && !resultHidden && (
        <GameOverOverlay game={state.game} onNewGame={onNewGame} onViewBoard={() => setResultHidden(true)} />
      )}
      <div className={`toolbar-actions${pickIndex !== null ? ' has-picker' : ''}`}>
        <div className="toolbar-leading">
          {/* Only buttons that can be clicked right now are shown. */}
          {humanTurnState === 'awaitingRoll' && (
            <button className="btn primary" onClick={() => sendAction({ type: 'roll' })} aria-keyshortcuts="d">
              Roll
            </button>
          )}
          {humanTurnState === 'choosingPlacement' && (
            <button className="btn secondary" onClick={rotate} aria-keyshortcuts="r">
              Rotate
            </button>
          )}
          {humanTurnState === 'skipped' && (
            <button className="btn secondary" onClick={() => sendAction({ type: 'skip' })} aria-keyshortcuts="s">
              Skip
            </button>
          )}
          {rerollUsable && (
            <button className="btn secondary" onClick={() => sendAction({ type: 'reroll' })} aria-keyshortcuts="e">
              Reroll
            </button>
          )}
        </div>
        {pickIndex !== null && (
          <div className="wildcard-picker">
            {/* The pills take the wildcard die's slot: leading when the server says editableIndex is 0. */}
            {pickIndex === 0 ? [pills, fixedDie] : [fixedDie, pills]}
          </div>
        )}
        {state && shownRoll && pickIndex === null && (
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
          <button className="btn secondary" onClick={onOpenSettings}>
            Menu
          </button>
        </div>
      </div>
    </div>
  )
}
