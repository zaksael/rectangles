import { useEffect, useRef, type ReactNode } from 'react'
import type { GameWireState, SeriesWireState } from '../game/gameTypes'
import { KeyBadge } from '../components/KeyBadge'
import { formatSigned, key, nameOf, reasonText } from '../game/resultText'
import { useAutoOpenDialog } from '../hooks/useAutoOpenDialog'


export const SELF_ENCLOSED_PENALTY_PER_CELL = 1 // fixed on the server, not sent on the wire or configurable per-game

interface ModifierRow {
  label: string
  note: (game: GameWireState) => string
  enabled: (game: GameWireState) => boolean
  value: (game: GameWireState, id: '1' | '2') => number
}

const MODIFIER_ROWS: ModifierRow[] = [
  {
    label: 'Prize',
    note: (game) => `+${game.houseRules.prize.points} per captured cell`,
    enabled: (game) => game.houseRules.prize.enabled,
    value: (game, id) => game.players[id].houseRules.prize.captured * game.houseRules.prize.points,
  },
  {
    label: 'Pitfall',
    note: (game) => `−${game.houseRules.pitfall.points} per captured cell`,
    enabled: (game) => game.houseRules.pitfall.enabled,
    value: (game, id) => -(game.players[id].houseRules.pitfall.captured * game.houseRules.pitfall.points),
  },
  {
    label: 'Steal',
    note: (game) => `capturer +${game.houseRules.steal.points}, opponent −${game.houseRules.steal.points}, per capture`,
    // Zero-sum: each capture adds to the capturer and docks the opponent by the same
    // amount, so a player's net is their own captures minus the opponent's, in points.
    enabled: (game) => game.houseRules.steal.enabled,
    value: (game, id) => {
      const opponent = id === '1' ? '2' : '1'
      const { captured: own } = game.players[id].houseRules.steal
      const { captured: theirs } = game.players[opponent].houseRules.steal
      return (own - theirs) * game.houseRules.steal.points
    },
  },
  {
    label: 'Enclosure',
    note: () => `−${SELF_ENCLOSED_PENALTY_PER_CELL} per sealed-in cell`,
    enabled: (game) => game.houseRules.selfEnclosedPenalty.enabled,
    value: (game, id) => -(game.players[id].houseRules.selfEnclosedPenalty.cells * SELF_ENCLOSED_PENALTY_PER_CELL),
  },
]

function scoreMargin(game: GameWireState): number | null {
  const { winner, reason } = game.gameOver
  // A surrendered game's winner can trail on score, so there's no margin to state.
  if (winner === null || reason === 'surrender') return null
  const margin = game.players[key(winner)].score.totalScore - game.players[key(3 - winner)].score.totalScore
  return margin > 0 ? margin : null
}

// The label of the modifier row whose gap between the players is largest, when it covers at least half the margin.
function biggestSwing(game: GameWireState, rows: ModifierRow[], margin: number): string | null {
  let best: { label: string; size: number } | null = null
  for (const row of rows) {
    const size = Math.abs(row.value(game, '1') - row.value(game, '2'))
    if (size > 0 && (best === null || size > best.size)) best = { label: row.label, size }
  }
  return best && best.size * 2 >= margin ? best.label : null
}

// A winner who trailed on territory is explained by the modifiers that went their way, not by the biggest swing.
function comebackClause(game: GameWireState, rows: ModifierRow[]): string | null {
  const { winner } = game.gameOver
  if (winner === null) return null
  const id = key(winner)
  const other = key(3 - winner)
  const trailedBy = game.players[other].score.totalArea - game.players[id].score.totalArea
  if (trailedBy <= 0) return null
  const turned = rows.filter((row) => row.value(game, id) > row.value(game, other)).map((row) => row.label)
  return turned.length ? `Trailed by ${trailedBy} on territory, won on ${new Intl.ListFormat('en-GB').format(turned)}.` : null
}

// The placed move with the largest rise in its mover's own score, when one move holds that gain alone and a special-cell rule is on.
function bestTurn(game: GameWireState): { turn: number; playerId: number; gain: number } | null {
  const { history } = game.gameOver
  const { prize, pitfall, steal } = game.houseRules
  if (!history || !(prize.enabled || pitfall.enabled || steal.enabled)) return null
  const gains = history.map((entry, i) => ({ turn: i + 1, playerId: entry.playerId, gain: entry.score[key(entry.playerId)] - (i === 0 ? 0 : history[i - 1].score[key(entry.playerId)]) }))
  const top = Math.max(...gains.map((g) => g.gain))
  const best = gains.filter((g) => g.gain === top)
  return top > 0 && best.length === 1 ? best[0] : null
}

const pointsText = (n: number) => `${n} ${n === 1 ? 'point' : 'points'}`

// The margin is shown bold; `detail` is the comeback sentence that follows it, when there is one.
interface Story {
  margin: string
  detail: string | null
}

function storyText(game: GameWireState, rows: ModifierRow[], margin: number | null): Story | null {
  if (margin === null) return null
  return { margin: pointsText(margin), detail: comebackClause(game, rows) }
}

function headlineText(game: GameWireState, inSeries = false): string {
  const { winner, reason } = game.gameOver
  if (inSeries) return winner === null ? 'Round tied' : `${nameOf(game, winner)} wins the round`
  return winner === null ? 'Tied' : `${nameOf(game, winner)} wins${reason === 'surrender' ? '' : ' on score'}`
}

// N is also the placement shortcut for the next legal spot, so for this long after the result appears (and while the key is held) it
// is ignored rather than starting something new from a stray press.
const ADVANCE_KEY_GUARD_MS = 500

// When N starts working: the guard after mount, kept in a ref that an effect sets because the clock is not read during render.
function useArmedAt() {
  const armedAt = useRef(Infinity)
  useEffect(() => {
    armedAt.current = Date.now() + ADVANCE_KEY_GUARD_MS
  }, [])
  return armedAt
}

// V goes back to the board or the result, N starts a new game, R opens the replay; Ctrl, Cmd and Alt combos belong to the browser.
function handleResultKey(event: { key: string; repeat: boolean; ctrlKey: boolean; metaKey: boolean; altKey: boolean }, armedAt: number, onView: () => void, onNewGame?: () => void, onReplay?: () => void) {
  if (event.ctrlKey || event.metaKey || event.altKey) return
  const key = event.key.toLowerCase()
  if (key === 'v') onView()
  else if (key === 'r') onReplay?.()
  else if (key === 'n' && !event.repeat && Date.now() >= armedAt) onNewGame?.()
}

// The breakdown tables' header: a hidden label for the row-title column, then one column per player.
function ScoreTableHead({ game, label }: { game: GameWireState; label: string }) {
  return (
    <thead>
      <tr>
        <th scope="col">
          <span className="visually-hidden">{label}</span>
        </th>
        {(['1', '2'] as const).map((id) => (
          <th key={id} scope="col">
            <span className={`swatch p${id}`} aria-hidden="true" />
            {nameOf(game, Number(id))}
          </th>
        ))}
      </tr>
    </thead>
  )
}

interface ResultDialogProps {
  winner: number | null
  describedBy?: string
  onViewBoard: () => void
  onAdvance?: () => void
  onReplay?: () => void
  children: ReactNode
}

// The dialog shell both result cards share. Escape shows the board rather than dismissing the result, so the native close is suppressed.
function ResultDialog({ winner, describedBy, onViewBoard, onAdvance, onReplay, children }: ResultDialogProps) {
  const dialogRef = useAutoOpenDialog()
  const armedAt = useArmedAt()
  return (
    <dialog
      className="modal game-over"
      data-outcome={winner ?? 'tie'}
      ref={dialogRef}
      onCancel={(e) => {
        e.preventDefault()
        onViewBoard()
      }}
      onKeyDown={(e) => handleResultKey(e, armedAt.current, onViewBoard, onAdvance, onReplay)}
      aria-labelledby="gameover-title"
      aria-describedby={describedBy}
    >
      {children}
    </dialog>
  )
}

// The result's last button, and the action N shares with it: New Game for a single game, Next Round mid-series,
// Series Result after the last round. A button whose handler wasn't given isn't shown.
function advanceFor(series: SeriesWireState | null, handlers: { onNewGame: () => void; onNextRound?: () => void; onSeriesResult?: () => void }) {
  if (series === null) return { label: 'New Game', onAdvance: handlers.onNewGame }
  return series.isComplete ? { label: 'Series Result', onAdvance: handlers.onSeriesResult } : { label: 'Next Round', onAdvance: handlers.onNextRound }
}

// A result button with its key chip (N by default; Replay uses R).
function AdvanceButton({ label, onAdvance, keyName = 'N' }: { label: string; onAdvance?: () => void; keyName?: string }) {
  if (!onAdvance) return null
  return (
    <button className="btn secondary" onClick={onAdvance} aria-keyshortcuts={keyName.toLowerCase()}>
      {label}
      <KeyBadge>{keyName}</KeyBadge>
    </button>
  )
}

// What is left of the result while the player looks at the final board: the outcome, and a way back.
interface GameOverBarProps {
  game: GameWireState
  series?: SeriesWireState | null
  onViewResult: () => void
  onNewGame: () => void
  onNextRound?: () => void
  onSeriesResult?: () => void
  // The bar for the series card's board view: the series outcome and totals, and no way forward but a new game.
  seriesResult?: boolean
}

export function GameOverBar({ game, series = null, seriesResult = false, onViewResult, onNewGame, onNextRound, onSeriesResult }: GameOverBarProps) {
  const advance = advanceFor(seriesResult ? null : series, { onNewGame, onNextRound, onSeriesResult })
  const armedAt = useArmedAt()
  const outcome =
    seriesResult && series
      ? { headline: seriesHeadline(game, series), reason: null, label: 'Series result' }
      : {
          headline: headlineText(game, series !== null),
          reason: game.gameOver.reason === 'boardFull' ? null : reasonText(game),
          label: 'Game result',
        }
  const { reason } = outcome
  // The bar is not a dialog, so it listens on the window and stands down while the Menu (or any dialog) is open.
  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (!document.querySelector('dialog[open]')) handleResultKey(event, armedAt.current, onViewResult, advance.onAdvance)
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [armedAt, onViewResult, advance.onAdvance])
  return (
    <div className="rail-turn" role="region" aria-label={outcome.label}>
      <div className="rail-instr">
        <div className="turn-status">{outcome.headline}</div>
        <p className="board-help">{reason}</p>
      </div>
      <div className={`rail-dice${game.houseRules.wildcard.enabled ? ' reserves-picker' : ''}`} />
      <div className="rail-actions">
        <button className="btn secondary" onClick={onViewResult} aria-keyshortcuts="v" autoFocus>
          View Result
          <KeyBadge>V</KeyBadge>
        </button>
        <AdvanceButton {...advance} />
      </div>
    </div>
  )
}

interface GameOverOverlayProps {
  game: GameWireState
  series?: SeriesWireState | null
  onNewGame: () => void
  onViewBoard: () => void
  onNextRound?: () => void
  onSeriesResult?: () => void
  onReplay?: () => void
}

export function GameOverOverlay({ game, series = null, onNewGame, onViewBoard, onNextRound, onSeriesResult, onReplay }: GameOverOverlayProps) {
  const { winner, reason: endReason } = game.gameOver
  // A series round says where it falls in the series; a settled board adds nothing to that.
  const detail = series === null ? reasonText(game) : [`Round ${series.gamesPlayed} of ${series.length}`, endReason !== 'boardFull' && reasonText(game)].filter(Boolean).join(' · ')
  // An enabled rule nobody triggered carries no information, so its row is left out.
  const rows = MODIFIER_ROWS.filter((row) => row.enabled(game) && (row.value(game, '1') !== 0 || row.value(game, '2') !== 0))
  const margin = scoreMargin(game)
  const swing = margin === null ? null : biggestSwing(game, rows, margin)
  const story = storyText(game, rows, margin)
  const best = bestTurn(game)
  const advance = advanceFor(series, { onNewGame, onNextRound, onSeriesResult })

  return (
    <ResultDialog winner={winner} describedBy={story ? 'gameover-story' : undefined} onViewBoard={onViewBoard} onAdvance={advance.onAdvance} onReplay={onReplay}>
      {detail && <p className="reason">{detail}</p>}
      <h2 id="gameover-title">
        {winner !== null && <span className={`dot p${winner}`} aria-hidden="true" />}
        {headlineText(game, series !== null)}
      </h2>
      {story && (
        <p className="game-over-story" id="gameover-story">
          by <b>{story.margin}</b>
          {story.detail && `. ${story.detail}`}
        </p>
      )}
      {best && (
        <p className="game-over-best">
          Best turn: <b>{`${nameOf(game, best.playerId)} scored +${best.gain} on turn ${best.turn}`}</b>
        </p>
      )}
      {endReason === 'surrender' && <p className="game-over-caption">Score at surrender</p>}
      <div className="game-over-scoreboard" role="group" aria-label={series === null ? 'Final score' : 'Round score'}>
        {(['1', '2'] as const).map((id) => {
          const won = winner === Number(id)
          // The winner of a surrendered game can trail, so muting the lower total would contradict the headline.
          return (
            <div key={id} className={`${winner === null || endReason === 'surrender' || won ? 'lead' : 'trail'}${won ? ' winner' : ''}`}>
              <div className="who">
                <span className={`swatch p${id}`} aria-hidden="true" />
                {nameOf(game, Number(id))}
              </div>
              <div className="n">{game.players[id].score.totalScore}</div>
              {series !== null && series.gamesPlayed >= 2 && <div className="series-total">{`Series ${series.scores[id]}${series.scores[id] > series.scores[key(3 - Number(id))] ? ' · leads' : ''}`}</div>}
            </div>
          )
        })}
      </div>
      {rows.length > 0 && (
        <table className="breakdown">
          <ScoreTableHead game={game} label="Score" />
          <tbody>
            <tr>
              <th scope="row">Territory</th>
              <td>{game.players['1'].score.totalArea}</td>
              <td>{game.players['2'].score.totalArea}</td>
            </tr>
            {rows.map((row) => (
              <tr key={row.label}>
                <th scope="row">
                  {row.label}
                  {swing === row.label && (
                    <>
                      <span className="visually-hidden">,</span>{' '}
                      <span className="game-over-swing-tag">Biggest swing</span>
                    </>
                  )}
                  <span className="game-over-row-note">{row.note(game)}</span>
                </th>
                {(['1', '2'] as const).map((id) => {
                  const value = row.value(game, id)
                  return (
                    <td key={id} className={value < 0 ? 'negative' : value === 0 ? 'zero' : undefined}>
                      {formatSigned(value)}
                    </td>
                  )
                })}
              </tr>
            ))}
          </tbody>
        </table>
      )}
      <div className="actions">
        <button className="btn primary" onClick={onViewBoard} aria-keyshortcuts="v" autoFocus>
          View Board
          <KeyBadge>V</KeyBadge>
        </button>
        <AdvanceButton {...advance} />
        <AdvanceButton label="Replay" onAdvance={onReplay} keyName="R" />
      </div>
    </ResultDialog>
  )
}

const seriesHeadline = (game: GameWireState, series: SeriesWireState) =>
  series.winner === null ? 'Series tied' : `${nameOf(game, series.winner)} wins the series`

// The series' result: a per-round ledger ending in the total that decided it.
export function SeriesResultOverlay({ game, series, onNewGame, onViewBoard, onReplay }: { game: GameWireState; series: SeriesWireState; onNewGame: () => void; onViewBoard: () => void; onReplay?: () => void }) {
  const { winner } = series
  return (
    <ResultDialog winner={winner} describedBy={winner !== null ? 'gameover-story' : undefined} onViewBoard={onViewBoard} onAdvance={onNewGame} onReplay={onReplay}>
      <p className="reason">{`${series.length} rounds · most points wins`}</p>
      <h2 id="gameover-title">
        {winner !== null && <span className={`dot p${winner}`} aria-hidden="true" />}
        {seriesHeadline(game, series)}
      </h2>
      {winner !== null && (
        <p className="game-over-story" id="gameover-story">
          by <b>{pointsText(Math.abs(series.scores['1'] - series.scores['2']))}</b>
        </p>
      )}
      <table className="breakdown">
        <ScoreTableHead game={game} label="Round" />
        <tbody>
          {series.rounds.map((round, index) => (
            <tr key={index}>
              <th scope="row">{`Round ${index + 1}`}</th>
              <td>{round.total['1']}</td>
              <td>{round.total['2']}</td>
            </tr>
          ))}
          <tr className="total">
            <th scope="row">Series total</th>
            {(['1', '2'] as const).map((id) => (
              <td key={id} className={winner === Number(id) ? 'win' : undefined}>
                {series.scores[id]}
              </td>
            ))}
          </tr>
        </tbody>
      </table>
      <div className="actions">
        <button className="btn primary" onClick={onViewBoard} aria-keyshortcuts="v" autoFocus>
          View Board
          <KeyBadge>V</KeyBadge>
        </button>
        <AdvanceButton label="New Game" onAdvance={onNewGame} />
        <AdvanceButton label="Replay Last Round" onAdvance={onReplay} keyName="R" />
      </div>
    </ResultDialog>
  )
}
