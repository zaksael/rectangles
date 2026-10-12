import { useEffect, type ReactNode } from 'react'
import { MIN_WINDOW_WIDTH, useNarrowWindow } from '../hooks/useNarrowWindow'
import './NarrowWindowGate.css'

const ADVICE = {
  Playing: 'Widen it to carry on: your game is paused where it was and nothing is lost.',
  Replay: 'Widen it to watch the replay: it stays on the turn you were on.',
}

// Below the minimum width the screen is hidden, not unmounted, so a game or a replay keeps its place; a notice stands in for it.
export function NarrowWindowGate({ screen, children }: { screen: keyof typeof ADVICE; children: ReactNode }) {
  const { narrow, width } = useNarrowWindow()
  // The hidden screen's own window key handlers must not act on a game nobody can see: a capture listener on the window runs
  // before any of them (the same target included) and ends the event there.
  useEffect(() => {
    if (!narrow) return
    const swallow = (event: KeyboardEvent) => event.stopImmediatePropagation()
    window.addEventListener('keydown', swallow, true)
    return () => window.removeEventListener('keydown', swallow, true)
  }, [narrow])
  return (
    <>
      <div hidden={narrow}>{children}</div>
      {narrow && (
        <div className="narrow-notice" role="status">
          <div className="narrow-notice-body">
            <div className="narrow-notice-reason">Window too narrow</div>
            <h1 className="title narrow-notice-title">Widen the Window</h1>
            <p className="narrow-notice-text">{`${screen} needs a window at least ${MIN_WINDOW_WIDTH}px wide, and yours is ${width}px. ${ADVICE[screen]}`}</p>
          </div>
        </div>
      )}
    </>
  )
}
