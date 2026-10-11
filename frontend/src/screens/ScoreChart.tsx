import { useLayoutEffect, useRef, useState, type FocusEvent, type KeyboardEvent } from 'react'
import type { HistoryEntry } from '../gameTypes'
import { formatSigned } from './GameOverOverlay'

// Plot margins in px: room for the y labels on the left and the turn numbers below.
const LEFT = 36
const RIGHT = 10
const TOP = 10
const BOTTOM = 26
const GRID_STEP = 25
const DEFAULT_SIZE = { width: 320, height: 300 }

const IDS = ['1', '2'] as const

// Both players' score after each turn, starting from 0 before the first one.
const seriesFor = (history: HistoryEntry[], id: '1' | '2') => [0, ...history.map((entry) => entry.score[id])]

// The box the chart fills; it follows the layout, which gives up height in a short window.
function useBoxSize() {
  const ref = useRef<HTMLDivElement>(null)
  const [size, setSize] = useState(DEFAULT_SIZE)
  useLayoutEffect(() => {
    if (!ref.current || typeof ResizeObserver === 'undefined') return
    const observer = new ResizeObserver(([entry]) => setSize({ width: entry.contentRect.width, height: entry.contentRect.height }))
    observer.observe(ref.current)
    return () => observer.disconnect()
  }, [])
  return [ref, size] as const
}

interface ScoreChartProps {
  history: HistoryEntry[]
  step: number
  names: { '1': string; '2': string }
  onJump: (turn: number) => void
  // Turns where a better move existed: each gets a ring on the mover's own dot.
  flagged?: number[]
}

export function ScoreChart({ history, step, names, onJump, flagged = [] }: ScoreChartProps) {
  const [ref, { width, height }] = useBoxSize()
  // The one tab stop: the turn that last had focus inside the chart, else the current turn.
  const [roving, setRoving] = useState<number | null>(null)
  const targets = useRef<(SVGRectElement | null)[]>([])
  const turns = history.length
  const series = { '1': seriesFor(history, '1'), '2': seriesFor(history, '2') }
  const all = [...series['1'], ...series['2']]
  const top = Math.max(GRID_STEP, Math.ceil(Math.max(...all) / GRID_STEP) * GRID_STEP)
  const bottom = Math.min(0, Math.floor(Math.min(...all) / GRID_STEP) * GRID_STEP)
  const x = (turn: number) => LEFT + (turn / turns) * (width - LEFT - RIGHT)
  const y = (score: number) => height - BOTTOM - ((score - bottom) / (top - bottom)) * (height - TOP - BOTTOM)
  const linePoints = (id: '1' | '2', from: number, to: number) =>
    series[id].slice(from, to + 1).map((score, i) => `${x(from + i)},${y(score)}`).join(' ')
  const tabStop = roving ?? step
  const targetWidth = (width - LEFT - RIGHT) / turns

  // Arrows, Home and End move focus (not the step); Enter and Space jump. They are the chart's own while it has focus.
  const onKeyDown = (e: KeyboardEvent<SVGRectElement>, turn: number) => {
    if (e.ctrlKey || e.metaKey || e.altKey) return
    const to: Record<string, number> = { ArrowRight: turn + 1, ArrowDown: turn + 1, ArrowLeft: turn - 1, ArrowUp: turn - 1, Home: 0, End: turns }
    if (e.key in to) targets.current[Math.max(0, Math.min(turns, to[e.key]))]?.focus()
    else if (e.key === 'Enter' || e.key === ' ') onJump(turn)
    else return
    e.preventDefault()
    e.stopPropagation()
  }
  const onBlur = (e: FocusEvent<SVGSVGElement>) => {
    if (!e.currentTarget.contains(e.relatedTarget)) setRoving(null)
  }
  const gridValues = Array.from({ length: (top - bottom) / GRID_STEP + 1 }, (_, i) => bottom + i * GRID_STEP)

  return (
    <div className="chart-wrap">
      <div className="chart-head">
        <span className="chart-label">Score history</span>
        {turns > 0 && (
          <>
            <span className="chart-readout">
              {IDS.map((id) => (
                <span key={id}>
                  <span className={`dot p${id}`} aria-hidden="true" />
                  <span className="visually-hidden">{`${names[id]} `}</span>
                  {formatSigned(series[id][step])}
                </span>
              ))}
              <span>{`Turn ${step}`}</span>
            </span>
            {flagged.length > 0 && (
              <span className="chart-key">
                <svg viewBox="0 0 14 14" aria-hidden="true">
                  <circle cx="7" cy="7" r="2.5" fill="var(--ink)" />
                  <circle cx="7" cy="7" r="6" fill="none" stroke="var(--ink)" strokeWidth="1.5" />
                </svg>
                Better move existed
              </span>
            )}
            <span className="chart-hint">Select a turn to jump to it</span>
          </>
        )}
      </div>
      <div className="chart-body" ref={ref}>
        {turns === 0 ? (
          <div className="chart-empty">Nothing to chart: no moves were played</div>
        ) : (
          <svg className="chart" role="group" aria-label={`Score history, ${names['1']} and ${names['2']}`} onBlur={onBlur} viewBox={`0 0 ${width} ${height}`} width={width} height={height}>
            {gridValues.map((value) => (
              <g key={value}>
                <line x1={LEFT} x2={width - RIGHT} y1={y(value)} y2={y(value)} stroke={value === 0 && bottom < 0 ? 'var(--ink)' : 'var(--line)'} strokeWidth={1} />
                <text x={LEFT - 12} y={y(value) + 4} textAnchor="end" className="chart-axis" aria-hidden="true">
                  {formatSigned(value)}
                </text>
              </g>
            ))}
            {Array.from({ length: turns + 1 }, (_, turn) => turn)
              .filter((turn) => turn % 5 === 0 || turn === turns)
              .map((turn) => (
                <text key={turn} x={x(turn)} y={height - 8} textAnchor="middle" className="chart-axis" aria-hidden="true">
                  {turn}
                </text>
              ))}
            {series['1'].map((_, turn) => (
              <rect
                key={turn}
                ref={(el) => void (targets.current[turn] = el)}
                className="chart-hit"
                x={x(turn) - targetWidth / 2}
                y={TOP}
                width={targetWidth}
                height={height - TOP - BOTTOM}
                role="button"
                tabIndex={turn === tabStop ? 0 : -1}
                aria-current={turn === step ? 'true' : undefined}
                aria-label={`Jump to turn ${turn}, ${names['1']} ${formatSigned(series['1'][turn])}, ${names['2']} ${formatSigned(series['2'][turn])}`}
                onClick={() => onJump(turn)}
                onFocus={() => setRoving(turn)}
                onKeyDown={(e) => onKeyDown(e, turn)}
              />
            ))}
            <line className="chart-marker" x1={x(step)} x2={x(step)} y1={TOP} y2={height - BOTTOM} stroke="var(--ink)" strokeWidth={1} />
            {IDS.map((id) => (
              <g key={id}>
                {step > 0 && <polyline className={`chart-line p${id} played`} points={linePoints(id, 0, step)} fill="none" stroke={`var(--p${id})`} strokeWidth={2} />}
                {step < turns && <polyline className={`chart-line p${id} ahead`} points={linePoints(id, step, turns)} fill="none" stroke={`var(--p${id})`} strokeWidth={2} opacity={0.35} />}
                {series[id].map((score, turn) => (
                  <circle
                    key={turn}
                    className={`chart-dot p${id}`}
                    cx={x(turn) + (turn === 0 ? (id === '1' ? -3 : 3) : 0)}
                    cy={y(score)}
                    r={turn === step ? 5 : 2.5}
                    fill={`var(--p${id})`}
                    opacity={turn > step ? 0.35 : 1}
                  />
                ))}
                {flagged
                  .filter((turn) => history[turn - 1]?.playerId === Number(id))
                  .map((turn) => (
                    <circle
                      key={`ring-${turn}`}
                      className={`chart-ring p${id}`}
                      cx={x(turn)}
                      cy={y(series[id][turn])}
                      r={turn === step ? 8.5 : 6}
                      fill="none"
                      stroke="var(--ink)"
                      strokeWidth={1.5}
                      opacity={turn > step ? 0.35 : 1}
                      aria-hidden="true"
                    />
                  ))}
              </g>
            ))}
          </svg>
        )}
      </div>
    </div>
  )
}
