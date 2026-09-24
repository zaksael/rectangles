import type { GameWireState, SeriesWireState } from '../gameTypes'
import { HOUSE_RULE_GROUPS } from '../houseRules'
import { useAutoOpenDialog } from '../useAutoOpenDialog'

interface SettingsOverlayProps {
  game: GameWireState
  series: SeriesWireState | null
  opponentLabel: string
  onClose: () => void
}

export function SettingsOverlay({ game, series, opponentLabel, onClose }: SettingsOverlayProps) {
  const dialogRef = useAutoOpenDialog()
  return (
    // Suppress the native auto-close so Escape routes through the same onClose as the button.
    <dialog
      className="modal settings"
      ref={dialogRef}
      aria-labelledby="settings-title"
      onCancel={(e) => {
        e.preventDefault()
        onClose()
      }}
    >
      <div className="settings-header">
        <button className="btn primary" onClick={onClose} autoFocus>
          <span aria-hidden="true">← </span>Resume
        </button>
        <h2 id="settings-title">Settings</h2>
      </div>
      <div className="settings-body">
        <dl className="match-info">
          <div>
            <dt>Opponent</dt>
            <dd>{opponentLabel}</dd>
          </div>
          <div>
            <dt>Board size</dt>
            <dd>
              {game.board.size}×{game.board.size}
            </dd>
          </div>
          <div>
            <dt>Skip limit</dt>
            <dd>{game.board.skipLimit}</dd>
          </div>
          {series && (
            <div>
              <dt>Series</dt>
              <dd>
                Round {series.gamesPlayed + 1} of {series.length}
              </dd>
            </div>
          )}
        </dl>
        <div className="settings-rules">
          {HOUSE_RULE_GROUPS.map((group) => (
            <section key={group.label}>
              <h3>{group.label}</h3>
              <ul>
                {group.rules.map((rule) => {
                  const wireKey = rule.key.replace(/Enabled$/, '') as keyof GameWireState['houseRules']
                  const on = game.houseRules[wireKey].enabled
                  return (
                    <li key={rule.key} className={on ? 'settings-rule on' : 'settings-rule'}>
                      <span className="settings-box" aria-hidden="true" />
                      <span>{rule.label}</span>
                      <span className="visually-hidden">{on ? 'On' : 'Off'}</span>
                    </li>
                  )
                })}
              </ul>
            </section>
          ))}
        </div>
      </div>
    </dialog>
  )
}
