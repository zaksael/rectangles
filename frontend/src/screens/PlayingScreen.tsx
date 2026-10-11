import { useEffect, useRef, useState } from 'react'
import { Board } from '../components/Board'
import { SpecialCellLegend } from '../components/SpecialCellLegend'
import { GameOverBar, GameOverOverlay, SeriesResultOverlay } from './GameOverOverlay'
import type { ErrorReason, GameAction, GameWireState, RecentTurn } from '../gameTypes'
import { ADJACENCY_RULE, placementReason, START_CORNER_RULE } from '../placementReason'
import { useLastPlaced } from '../useLastPlaced'
import { usePlacementInput } from '../usePlacementInput'
import type { GameError, GameState } from '../useGameSocket'
import { KeyBadge } from '../components/KeyBadge'
import { noBreak } from '../noBreak'
import { RULE_ROWS, signed } from '../ruleRows'
import { seriesRound } from '../seriesRound'
import { coveredSpecialRules } from '../specialCells'
import './ScoreTable.css'
import './PlayingScreen.css'

interface PlayingScreenProps {
  state: GameState | null
  error: GameError | null
  sendAction: (action: GameAction) => void
  onOpenSettings: () => void
  onNewGame: () => void
  // Says which card Replay was opened from, so Back can show that card again.
  onReplay?: (fromSeriesResult: boolean) => void
  // Back from Replay on a finished series: open the series card rather than the last round's.
  initialSeriesResultOpen?: boolean
  botSeat?: number
}

const ERROR_TOAST_MS = 4000
// A Comeback grant is easy to miss, so its notice stays twice as long as an error toast.
const COMEBACK_TOAST_MS = 8000

// The key that applies in each of the human's turn states; other states show a blank line.
const KEY_HINT: Partial<Record<string, string>> = {
  choosingPlacement: 'Arrows move, N next, Enter places, R rotates',
}

function boardSummary(game: GameWireState) {
  const count = (n: number, noun: string) => `${n} ${noun}${n === 1 ? '' : 's'}`
  const { obstacles, walls } = game.houseRules
  const parts = (['1', '2'] as const).map((id) => {
    const p = game.players[id]
    return `${p.name}: ${count(p.board.pieces.length, 'piece')}, ${count(p.score.totalArea, 'cell')}.`
  })
  if (obstacles.enabled) parts.push(`${count(obstacles.cells.length, 'obstacle cell')}.`)
  if (walls.enabled) parts.push(`${count(walls.edges.length, 'wall')}.`)
  return parts.join(' ')
}

function liveMoveText(turnState: string | undefined, size: readonly number[] | null) {
  if (turnState === 'awaitingRoll') return 'Waiting to roll…'
  if (turnState === 'choosingWildcard') return 'Wildcard roll, picking…'
  if (turnState === 'skipped') return 'No legal move, deciding…'
  return size ? `Placing ${size[0]} × ${size[1]}…` : 'Placing…'
}

function movedText(r: RecentTurn) {
  if (!r.placed) return 'No legal move, skipped'
  const wildcard = r.wildcardOriginalRoll ? `, wildcard (rolled ${r.wildcardOriginalRoll[0]}·${r.wildcardOriginalRoll[1]})` : ''
  return `Placed ${r.placed.width} × ${r.placed.height}${wildcard}`
}

const ERROR_TEXT: Record<ErrorReason, string> = {
  illegalPlacement: 'That piece can’t go there — try another spot.',
  invalidAction: 'You can’t do that right now — finish your current step.',
  protocolVersionMismatch: 'This game is out of date — reload the page.',
  illegalWildcardValue: 'That number can’t be placed — pick another.',
  malformedMessage: 'Something went wrong — try again.',
}

export function PlayingScreen({ state, error, sendAction, onOpenSettings, onNewGame, onReplay, initialSeriesResultOpen = false, botSeat }: PlayingScreenProps) {
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
  // After the last round, the series card sits on top of the round card until the next game.
  const [seriesResultOpen, setSeriesResultOpen] = useState(initialSeriesResultOpen)
  // A new round is a fresh game, so its result starts out shown.
  useEffect(() => {
    if (turnState !== 'gameOver') {
      setResultHidden(false)
      setSeriesResultOpen(false)
    }
  }, [turnState])
  const openSeriesResult = () => setSeriesResultOpen(true)
  const nextRound = () => sendAction({ type: 'continueSeries' })
  const grantedRef = useRef<Record<'1' | '2', boolean> | null>(null)
  useEffect(() => {
    if (!state) return
    const now = { '1': state.game.players['1'].houseRules.comebackNudge.granted, '2': state.game.players['2'].houseRules.comebackNudge.granted }
    const before = grantedRef.current ?? now
    grantedRef.current = now
    const newly = (['1', '2'] as const).find((id) => now[id] && !before[id])
    if (newly) setComebackNotice(`Comeback! ${noBreak(state.game.players[newly].name)} gets +1 reroll`)
  }, [state])

  // The notice row holds one notice: an error shows first, and a Comeback notice waits (its timer unstarted) until it clears.
  const errorShown = error !== null && error !== dismissedError
  useEffect(() => {
    if (!comebackNotice || errorShown) return
    const timer = setTimeout(() => setComebackNotice(null), COMEBACK_TOAST_MS)
    return () => clearTimeout(timer)
  }, [comebackNotice, errorShown])

  const sendActionRef = useRef(sendAction)
  sendActionRef.current = sendAction
  const openSettingsRef = useRef(onOpenSettings)
  openSettingsRef.current = onOpenSettings

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
  // Nobody is to move once the game is over, so the last roll goes, and the next round does not open on it.
  if (turnState === 'gameOver') lastRollRef.current = null
  else if (roll && state) lastRollRef.current = { values: roll, owner: String(state.game.turn.currentPlayerId) as '1' | '2' }
  const shownRoll = lastRollRef.current
  const rollLabel = shownRoll && state ? `${state.game.players[shownRoll.owner].name}${roll ? ' rolled' : '’s last roll'} ${shownRoll.values.join(' and ')}` : ''

  // In board view the result bar takes the header's place, so the player cells are not rendered.
  const showResultBar = turnState === 'gameOver' && resultHidden
  // Once the game is over nobody is to move, so the header stops marking a player.
  const currentId = turnState === 'gameOver' ? null : state?.game.turn.currentPlayerId
  const currentName = state && noBreak(state.game.players[String(state.game.turn.currentPlayerId) as '1' | '2'].name)
  let turnStatus: string | null = null
  if (currentName && turnState !== 'gameOver') {
    if (isBotTurn) turnStatus = `${currentName} is playing…`
    else if (turnState === 'awaitingRoll') {
      turnStatus = `${currentName}: roll (D)`
    }
    else if (turnState === 'choosingPlacement') {
      turnStatus = `${currentName}: place ${dims ? `${dims[0]} wide × ${dims[1]} tall` : 'a rectangle'}`
      const reason =
        previewKind === 'danger' && previewTopLeft && dims && state
          ? placementReason(state.game, state.game.turn.currentPlayerId as 1 | 2, previewTopLeft, dims)
          : null
      const firstMove = state.game.players[String(state.game.turn.currentPlayerId) as '1' | '2'].board.pieces.length === 0
      if (reason) turnStatus += ` — ${reason}`
      else if (previewKind !== 'legal') turnStatus += ` — ${firstMove ? START_CORNER_RULE : ADJACENCY_RULE}`
      else if (previewTopLeft && dims) {
        const covered = coveredSpecialRules(state.game, previewTopLeft, dims)
        if (covered.length > 0) turnStatus += ` — covers ${covered.join(', ')}`
      }
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
      if (key === 'm') {
        openSettingsRef.current()
      } else if (key === 'd' && humanTurnState === 'awaitingRoll') {
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

  const ids = ['1', '2'] as const
  const recentTurns = state?.game.turn.recentTurns ?? []
  // A game in progress can't be resumed once the tab is gone, so ask first (the browser words the prompt itself).
  const leaveGuarded = turnState !== 'gameOver' && recentTurns.length > 0
  useEffect(() => {
    if (!leaveGuarded) return
    const guard = (event: BeforeUnloadEvent) => event.preventDefault()
    window.addEventListener('beforeunload', guard)
    return () => window.removeEventListener('beforeunload', guard)
  }, [leaveGuarded])
  const liveRow = turnState !== 'gameOver' && state
  const moveRows = [
    ...(liveRow
      ? [{ turn: (recentTurns.at(-1)?.turn ?? 0) + 1, playerId: state.game.turn.currentPlayerId, live: true, text: liveMoveText(turnState, dims ?? roll), points: 0 }]
      : []),
    ...recentTurns
      .slice(liveRow ? -3 : -4)
      .reverse()
      .map((r) => ({ turn: r.turn, playerId: r.playerId, live: false, text: movedText(r), points: r.points })),
  ]
  const reroll = (id: '1' | '2') => state!.game.players[id].houseRules.reroll
  const title = state?.series ? `Round ${seriesRound(state.game, state.series)} of ${state.series.length}` : 'Game'

  return (
    <div className="playing">
      <h1 className="visually-hidden">Playing</h1>
      {state && (
        <div className="board-wrap">
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
            describedBy={placing ? 'board-help board-summary' : 'board-summary'}
          />
          {/* The dice are an image, which a screen reader doesn't announce when it changes; only a live roll is read out. */}
          <div className="visually-hidden" data-testid="roll-announcement" aria-live="polite">
            {roll ? rollLabel : ''}
          </div>
          <p id="board-summary" className="visually-hidden">{boardSummary(state.game)}</p>
          <div className="visually-hidden" data-testid="cursor-position" aria-live="polite">
            {previewTopLeft ? `Row ${previewTopLeft[0] + 1}, column ${previewTopLeft[1] + 1}` : ''}
          </div>
        </div>
      )}
      <div className="rail">
        <div className="rail-head">
          <h2 className="rail-title">{title}</h2>
          {state?.series && <span className="rail-series">{`Series ${state.series.scores['1']} – ${state.series.scores['2']}`}</span>}
          <button className="btn secondary" onClick={onOpenSettings} aria-keyshortcuts="m">
            Menu
            <KeyBadge>M</KeyBadge>
          </button>
        </div>
        {state && (
          <>
            <table className="score-table">
              <caption className="visually-hidden">Score</caption>
              <thead>
                <tr>
                  <td />
                  {ids.map((id) => (
                    <th key={id} scope="col" className={`p${id}${currentId === Number(id) ? ' current' : ''}${turnState === 'gameOver' ? ' over' : ''}`} aria-current={currentId === Number(id) ? 'true' : undefined}>
                      <span className="dot" aria-hidden="true" />
                      {state.game.players[id].name}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                <tr>
                  <th scope="row">Area</th>
                  {ids.map((id) => <td key={id}>{state.game.players[id].score.breakdown.area}</td>)}
                </tr>
                {RULE_ROWS.filter((row) => row.on(state.game)).map((row) => (
                  <tr key={row.label}>
                    <th scope="row">{row.label}</th>
                    {ids.map((id) => {
                      const value = state.game.players[id].score.breakdown[row.part]
                      return (
                        <td key={id} className={value === 0 ? 'zero' : undefined}>
                          {signed(value)}
                        </td>
                      )
                    })}
                  </tr>
                ))}
                <tr className="score-row">
                  <th scope="row">Score</th>
                  {ids.map((id) => <td key={id}>{state.game.players[id].score.totalScore}</td>)}
                </tr>
                <tr className="res-first">
                  <th scope="row">In reach</th>
                  {ids.map((id) => <td key={id}>{state.game.players[id].score.potential.area}</td>)}
                </tr>
                <tr>
                  <th scope="row">Skips</th>
                  {ids.map((id) => (
                    <td key={id} className={state.game.players[id].board.consecutiveSkips + 1 >= state.game.board.skipLimit ? 'last-skip' : undefined}>
                      {state.game.players[id].board.consecutiveSkips} / {state.game.board.skipLimit}
                    </td>
                  ))}
                </tr>
                {rerollEnabled && (
                  <tr>
                    <th scope="row">Rerolls</th>
                    {ids.map((id) => <td key={id}>{reroll(id).limit - reroll(id).used} / {reroll(id).limit}</td>)}
                  </tr>
                )}
              </tbody>
            </table>
            <SpecialCellLegend game={state.game} />
            <div className="rail-notice" role="status" aria-live="polite">
              {errorShown ? <div className="toast">{ERROR_TEXT[error.reason]}</div> : comebackNotice && <div className="toast">{comebackNotice}</div>}
            </div>
            {showResultBar ? (
              <GameOverBar game={state.game} series={state.series} seriesResult={seriesResultOpen} onViewResult={() => setResultHidden(false)} onNewGame={onNewGame} onNextRound={nextRound} onSeriesResult={openSeriesResult} />
            ) : (
              <div className="rail-turn">
                <div className="rail-instr">
                  {turnStatus && (
                    <div className="turn-status" data-testid="turn-status" aria-live="polite" aria-atomic="true">
                      {turnStatus}
                    </div>
                  )}
                  {/* Always rendered (blank when no key applies) so the status line doesn't shift vertically. */}
                  <p id="board-help" className="board-help">
                    {boardHint}
                  </p>
                </div>
                {/* Always rendered, at the picker's height while the Wildcard rule is on, so the buttons below never move. */}
                <div className={`rail-dice${wildcard?.enabled ? ' reserves-picker' : ''}`}>
                  {pickIndex !== null && (
                    <div className="wildcard-picker">
                      {/* The pills take the wildcard die's slot: leading when the server says editableIndex is 0. */}
                      {pickIndex === 0 ? [pills, fixedDie] : [fixedDie, pills]}
                    </div>
                  )}
                  {shownRoll && pickIndex === null && (
                    <div
                      className={`dice${roll ? '' : ' stale'}`}
                      role="img"
                      aria-label={rollLabel}
                    >
                      {shownRoll.values.map((value, i) => (
                        <span key={i} className="die">
                          {value}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
                <div className="rail-actions">
                  {/* Only buttons that can be clicked right now are shown. */}
                  {humanTurnState === 'awaitingRoll' && (
                    <button className="btn primary" onClick={() => sendAction({ type: 'roll' })} aria-keyshortcuts="d">
                      Roll
                      <KeyBadge>D</KeyBadge>
                    </button>
                  )}
                  {humanTurnState === 'choosingPlacement' && (
                    <button className="btn secondary" onClick={rotate} aria-keyshortcuts="r">
                      Rotate
                      <KeyBadge>R</KeyBadge>
                    </button>
                  )}
                  {humanTurnState === 'skipped' && (
                    <button className="btn secondary" onClick={() => sendAction({ type: 'skip' })} aria-keyshortcuts="s">
                      Skip
                      <KeyBadge>S</KeyBadge>
                    </button>
                  )}
                  {rerollUsable && (
                    <button className="btn secondary" onClick={() => sendAction({ type: 'reroll' })} aria-keyshortcuts="e">
                      Reroll
                      <KeyBadge>E</KeyBadge>
                    </button>
                  )}
                </div>
              </div>
            )}
            <div className="rail-history">
              <h2 className="rail-h" id="moves-heading">Moves</h2>
              <ol className="history" role="log" aria-live="off" aria-labelledby="moves-heading">
                {moveRows.map((m) => (
                  <li key={m.turn} className={`move p${m.playerId}${m.live ? ' live' : ''}`}>
                    <span className="turn-no">{m.turn}</span>
                    <span className="dot" aria-hidden="true" />
                    <span className="who">{state.game.players[String(m.playerId) as '1' | '2'].name}</span>
                    <span className="what">{m.text}</span>
                    <span className="gain">{m.points === 0 ? '' : signed(m.points)}</span>
                  </li>
                ))}
              </ol>
              {recentTurns.length === 0 && <p className="rail-empty">Nothing played yet</p>}
            </div>
          </>
        )}
      </div>
      {state && turnState === 'gameOver' && !resultHidden &&
        (seriesResultOpen && state.series ? (
          <SeriesResultOverlay game={state.game} series={state.series} onNewGame={onNewGame} onViewBoard={() => setResultHidden(true)} onReplay={onReplay && (() => onReplay(true))} />
        ) : (
          <GameOverOverlay game={state.game} series={state.series} onNewGame={onNewGame} onViewBoard={() => setResultHidden(true)} onNextRound={nextRound} onSeriesResult={openSeriesResult} onReplay={onReplay && (() => onReplay(false))} />
        ))}
    </div>
  )
}
