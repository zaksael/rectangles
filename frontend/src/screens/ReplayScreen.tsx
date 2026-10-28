import { useEffect, useEffectEvent, useState } from 'react'
import { Board } from '../components/Board'
import type { Analysis, AnalysisTurn, GameWireState, HistoryEntry, PieceState, ScoreParts, SeriesWireState } from '../game/gameTypes'
import { noBreak } from '../game/noBreak'
import { formatSigned, reasonText } from '../game/resultText'
import { ScoreChart } from '../components/ScoreChart'
import { RuleRowLabel } from '../components/RuleRowLabel'
import { ReachNoteRow, REACH_NOTE_ID } from '../components/ReachNoteRow'
import { RULE_ROWS, SELF_ENCLOSED_PENALTY_PER_CELL, signed } from '../game/ruleRows'
import { useNarrowWindow } from '../hooks/useNarrowWindow'
import '../components/ScoreTable.css'
import './ReplayScreen.css'

// The board as it stood after the first `step` moves: the final game's rules and special cells, with only those pieces on it.
function gameAt(game: GameWireState, history: HistoryEntry[], step: number): GameWireState {
  const piecesOf = (id: 1 | 2): PieceState[] =>
    history.slice(0, step).flatMap((entry) => (entry.playerId === id && entry.placed ? [{ ...entry.placed, owner: id }] : []))
  const player = (id: 1 | 2) => ({ ...game.players[id], board: { ...game.players[id].board, pieces: piecesOf(id) } })
  return { ...game, players: { '1': player(1), '2': player(2) } }
}

const rollText = (roll: [number, number]) => roll.join(', ')

function moveText(game: GameWireState, entry: HistoryEntry): string {
  const name = noBreak(game.players[String(entry.playerId) as '1' | '2'].name)
  const { placed, wildcardOriginalRoll } = entry
  if (!placed) return `${name} skipped (rolled ${rollText(entry.roll)})`
  const [row, col] = placed.topLeft
  const wildcard = wildcardOriginalRoll ? ` (wildcard: rolled ${rollText(wildcardOriginalRoll)})` : ''
  // 1-based, named as Playing's cursor reads the same cell.
  return `${name} placed a ${placed.width}×${placed.height} rectangle at row ${row + 1}, column ${col + 1}${wildcard}`
}

const ZERO_PARTS: ScoreParts = { area: 0, prize: 0, pitfall: 0, steal: 0, enclosure: 0 }

// What the placing player's score parts gained or lost on this step, named the way the rules read.
function effectTexts(game: GameWireState, history: HistoryEntry[], step: number): string[] {
  const entry = history[step - 1]!
  const me = String(entry.playerId) as '1' | '2'
  const opponent = noBreak(game.players[me === '1' ? '2' : '1'].name)
  const before = step === 1 ? ZERO_PARTS : history[step - 2]!.breakdown[me]
  const now = entry.breakdown[me]
  const gained = (part: keyof ScoreParts) => now[part] - before[part]
  const texts: string[] = []
  if (gained('prize') > 0) texts.push(`captures Prize (+${gained('prize')})`)
  if (gained('steal') > 0) texts.push(`captures Steal (+${gained('steal')}, ${opponent} −${gained('steal')})`)
  if (gained('pitfall') < 0) texts.push(`hits Pitfall (−${-gained('pitfall')})`)
  if (gained('enclosure') < 0) texts.push(`encloses ${-gained('enclosure') / SELF_ENCLOSED_PENALTY_PER_CELL} of its own cells (−${-gained('enclosure')})`)
  return texts
}

// The last step ends on why the game stopped, then who won; a surrender names its winner only, since the surrender decides it, not the score.
function endText(game: GameWireState, history: HistoryEntry[]): string | null {
  const reason = reasonText(game)
  const { winner } = game.gameOver
  if (game.gameOver.reason === 'surrender' && winner !== null) return `${reason}, ${noBreak(game.players[String(winner) as '1' | '2'].name)} wins`
  const { score } = history[history.length - 1]!
  const result = winner === null ? 'tied' : `${noBreak(game.players[String(winner) as '1' | '2'].name)} wins by ${Math.abs(score['1'] - score['2'])}`
  return reason && `${reason}, ${result}`
}

function Caption({ game, history, step }: { game: GameWireState; history: HistoryEntry[]; step: number }) {
  const notes = step === 0 ? [] : [...effectTexts(game, history, step), step === history.length ? endText(game, history) : null].filter(Boolean)
  return (
    <p className="caption" data-testid="replay-caption" aria-live="polite">
      {step === 0 ? (
        <>
          <span className="step">Start of game</span>No moves played yet
        </>
      ) : (
        <>
          <span className="step">{`Turn ${step} of ${history.length}`}</span>
          {moveText(game, history[step - 1]!) + (notes.length ? ` — ${notes.join(', ')}` : '')}
        </>
      )}
    </p>
  )
}

const AXIS_LABELS: Record<AnalysisTurn['axis'], string> = { prize: 'Prize', pitfall: 'Pitfall', steal: 'Steal', denial: 'Denial', enclosure: 'Enclosure' }

// Denial is counted in cells; the other axes are real points, named by the rule that drove the gap.
function analysisText({ axis, chosen, best }: AnalysisTurn): string {
  if (axis === 'denial') return `Denied ${chosen} ${chosen === 1 ? 'cell' : 'cells'} this turn; the best move denied ${best}`
  return `Scored ${formatSigned(chosen)} this turn; the best move scored ${formatSigned(best)} (${AXIS_LABELS[axis]})`
}

// The note for a flagged turn, or the one muted line saying why there is none.
function AnalysisLine({
  analysis,
  flaggedTurn,
  showBetterOption,
  onToggleBetterOption,
}: {
  analysis: Analysis
  flaggedTurn: AnalysisTurn | undefined
  showBetterOption: boolean
  onToggleBetterOption: () => void
}) {
  if (analysis.status === 'loading') {
    return (
      <p className="analysis pending" role="status">
        Checking for better moves…
      </p>
    )
  }
  if (analysis.status === 'unavailable') return <p className="analysis pending">Turn analysis unavailable</p>
  if (analysis.turns.length === 0) return <p className="analysis pending">No better moves found</p>
  if (!flaggedTurn) return null
  const text = analysisText(flaggedTurn)
  // A note this long would wrap to three lines beside the toggle, so the toggle takes its own row.
  return (
    <div className="analysis">
      <div className={`analysis-row${text.length > 50 ? ' stacked' : ''}`}>
        <span>{text}</span>
        <button className="btn secondary" aria-pressed={showBetterOption} onClick={onToggleBetterOption}>
          Show Better Option
        </button>
      </div>
    </div>
  )
}

// Each rule's share of both players' scores at the step, so the total can be read as a sum; In reach is the cells each
// player can still reach, which the wire carries per played move, so the start of the game has no figure.
function ScoreTable({ game, history, step }: { game: GameWireState; history: HistoryEntry[]; step: number }) {
  const at = history[step - 1]
  const ids = ['1', '2'] as const
  return (
    <table className="score-table">
      <caption className="visually-hidden">{`Score at ${step === 0 ? 'the start of the game' : `turn ${step}`}`}</caption>
      <thead>
        <tr>
          <td />
          {ids.map((id) => (
            <th key={id} scope="col" className="over">
              <span className={`dot p${id}`} aria-hidden="true" />
              {game.players[id].name}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        <tr>
          <th scope="row">Area</th>
          {ids.map((id) => (
            <td key={id}>{at ? at.breakdown[id].area : 0}</td>
          ))}
        </tr>
        {RULE_ROWS.filter((row) => row.on(game)).map((row) => (
          <tr key={row.label}>
            <th scope="row">
              <RuleRowLabel row={row} game={game} />
            </th>
            {ids.map((id) => {
              const value = at ? at.breakdown[id][row.part] : 0
              return (
                <td key={id} className={value === 0 ? 'zero' : undefined}>
                  {signed(value)}
                </td>
              )
            })}
          </tr>
        ))}
      </tbody>
      <tfoot>
        <tr>
          <th scope="row">Total</th>
          {ids.map((id) => (
            <td key={id}>{formatSigned(at ? at.score[id] : 0)}</td>
          ))}
        </tr>
        <tr className="res-first">
          <th scope="row" aria-describedby={REACH_NOTE_ID}>In reach</th>
          {ids.map((id) => (
            <td key={id} className={at ? undefined : 'zero'}>
              {at ? at.potential[id].area : '–'}
            </td>
          ))}
        </tr>
        <ReachNoteRow />
      </tfoot>
    </table>
  )
}

// One step every this many milliseconds, the same for a skip as for a placement.
const SPEEDS = [
  { label: 'Slow', ms: 1200 },
  { label: 'Normal', ms: 600 },
  { label: 'Fast', ms: 250 },
] as const

interface ReplayScreenProps {
  game: GameWireState
  series?: SeriesWireState | null
  onBack: () => void
  analysis?: Analysis | null
  showBetterOption?: boolean
  onToggleBetterOption?: () => void
  // The socket dropped: the replay needs no server, so it says so and carries on.
  connectionLost?: boolean
  onNewGame?: () => void
}

export function ReplayScreen({ game, series = null, onBack, analysis = null, showBetterOption = false, onToggleBetterOption = () => {}, connectionLost = false, onNewGame = () => {} }: ReplayScreenProps) {
  const history = game.gameOver.history ?? []
  const [step, setStep] = useState(0)
  const [playing, setPlaying] = useState(false)
  // Behind the narrow-window notice nobody is watching, so the replay holds the turn it was on.
  const { narrow } = useNarrowWindow()
  if (narrow && playing) setPlaying(false)
  const [speed, setSpeed] = useState<(typeof SPEEDS)[number]>(SPEEDS[1])
  const lastPlaced = history[step - 1]?.placed?.topLeft ?? null
  const atEnd = step === history.length
  const flaggedTurn = analysis?.status === 'ready' ? analysis.turns.find((t) => t.turn === step) : undefined

  useEffect(() => {
    if (!playing) return
    const timer = setTimeout(() => {
      setStep(step + 1)
      if (step + 1 === history.length) setPlaying(false)
    }, speed.ms)
    return () => clearTimeout(timer)
  }, [playing, step, speed, history.length])

  // Stepping by hand takes over from autoplay.
  const goTo = (to: (step: number) => number) => {
    setPlaying(false)
    setStep((s) => Math.max(0, Math.min(history.length, to(s))))
  }
  const togglePlay = () => {
    if (!playing && atEnd) setStep(0)
    setPlaying(!playing)
  }

  // Keys work from anywhere on the screen (the chart's own arrows come with the chart). Space is swallowed even on a focused
  // button, so it plays instead of also pressing that button; Enter keeps its native action.
  const actions: Record<string, () => void> = {
    ArrowRight: () => goTo((s) => s + 1),
    ArrowDown: () => goTo((s) => s + 1),
    ArrowLeft: () => goTo((s) => s - 1),
    ArrowUp: () => goTo((s) => s - 1),
    Home: () => goTo(() => 0),
    End: () => goTo(() => history.length),
    ' ': () => history.length > 0 && togglePlay(),
    Escape: onBack,
  }
  const handled = (e: KeyboardEvent) => !(e.ctrlKey || e.metaKey || e.altKey) && e.key in actions
  // One pair of listeners, bound once: the Effect Events always see this render's step and callbacks.
  const handleKeyDown = useEffectEvent((e: KeyboardEvent) => {
    if (!handled(e)) return
    e.preventDefault()
    actions[e.key]!()
  })
  const handleKeyUp = useEffectEvent((e: KeyboardEvent) => e.key === ' ' && handled(e) && e.preventDefault())
  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => handleKeyDown(e)
    const onKeyUp = (e: KeyboardEvent) => handleKeyUp(e)
    window.addEventListener('keydown', onKeyDown)
    window.addEventListener('keyup', onKeyUp)
    return () => {
      window.removeEventListener('keydown', onKeyDown)
      window.removeEventListener('keyup', onKeyUp)
    }
  }, [])

  return (
    <main className="replay">
      <div className="board-wrap">
        <Board game={gameAt(game, history, step)} lastPlaced={lastPlaced} betterOption={showBetterOption ? flaggedTurn : null} />
      </div>
      <aside className="rail" aria-label="Replay controls">
        <div className="rail-head">
          <h1 className="rail-title">Replay</h1>
          {series && (
            <span className="rail-series">
              <span>{`Round ${series.gamesPlayed} of ${series.length}`}</span>
              <span>{`Series ${series.scores['1']} – ${series.scores['2']}`}</span>
            </span>
          )}
          <button className="btn secondary" onClick={onBack}>Back</button>
        </div>
        {connectionLost && (
          <div className="conn-notice" role="status">
            <span>Connection lost. This replay still works.</span>
            <button className="btn secondary" onClick={onNewGame}>New Game</button>
          </div>
        )}
        <ScoreTable game={game} history={history} step={step} />
        <Caption game={game} history={history} step={step} />
        {analysis && (
          <div className="analysis-slot">
            <AnalysisLine analysis={analysis} flaggedTurn={flaggedTurn} showBetterOption={showBetterOption} onToggleBetterOption={onToggleBetterOption} />
          </div>
        )}
        <ScoreChart flagged={analysis?.status === 'ready' ? analysis.turns.map((t) => t.turn) : []} history={history} step={step} names={{ '1': game.players['1'].name, '2': game.players['2'].name }} onJump={(turn) => goTo(() => turn)} />
        <div className="controls">
          <div className="transport">
            <button className="btn secondary" disabled={step === 0} onClick={() => goTo(() => 0)}>First</button>
            <button className="btn secondary" disabled={step === 0} onClick={() => goTo((s) => s - 1)}>Prev</button>
            <button className={`btn secondary play${playing ? ' playing' : ''}`} disabled={history.length === 0} onClick={togglePlay}>{playing ? 'Pause' : 'Play'}</button>
            <button className="btn secondary" disabled={atEnd} onClick={() => goTo((s) => s + 1)}>Next</button>
            <button className="btn secondary" disabled={atEnd} onClick={() => goTo(() => history.length)}>Last</button>
          </div>
          <div className="speed" role="group" aria-label="Playback speed">
            {SPEEDS.map((option) => (
              <button key={option.label} className="btn secondary" aria-pressed={option === speed} onClick={() => setSpeed(option)}>
                {option.label}
              </button>
            ))}
          </div>
          <p className="controls-hint">Arrows step, Home/End jump, Space plays, Esc goes back</p>
        </div>
      </aside>
    </main>
  )
}
