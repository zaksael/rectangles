import { formatSigned } from '../game/resultText'
import { scoreShare } from '../game/scoreShare'
import './ScoreBar.css'

type Props = { names: readonly [string, string]; scores: readonly [number, number] }

// One bar of true share above the score table. The labels sit above both segments, so a segment with no width still shows its number.
export function ScoreBar({ names, scores }: Props) {
  const [a, b] = scores
  const share = scoreShare(a, b)
  return (
    <div className="score-bar" role="img" aria-label={`Score: ${names[0]} ${formatSigned(a)}, ${names[1]} ${formatSigned(b)}`}>
      <i className="score-bar-seg score-bar-p1" style={{ width: `${share}%` }} />
      <i className="score-bar-seg score-bar-p2" style={{ width: `${100 - share}%` }} />
      <span className="score-bar-num left">{formatSigned(a)}</span>
      <span className="score-bar-num right">{formatSigned(b)}</span>
    </div>
  )
}
