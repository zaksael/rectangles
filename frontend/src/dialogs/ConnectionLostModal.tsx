import { useAutoOpenDialog } from '../hooks/useAutoOpenDialog'

interface ConnectionLostModalProps {
  isSeries: boolean
  onNewGame: () => void
  // The server answered a stale page with a protocol version mismatch: reloading is the only way out.
  outOfDate?: boolean | undefined
  onReload?: (() => void) | undefined
}

export function ConnectionLostModal({ isSeries, onNewGame, outOfDate = false, onReload }: ConnectionLostModalProps) {
  const dialogRef = useAutoOpenDialog()

  const body = outOfDate
    ? 'The server was updated after this page loaded. Reload the page to continue.'
    : isSeries
    ? "The connection to the server dropped and couldn't be restored. Rejoining an in-progress game isn't supported yet, and the series can't be resumed either — you'll need to start a new one."
    : "The connection to the server dropped and couldn't be restored. Rejoining an in-progress game isn't supported yet — you'll need to start a new one."

  return (
    <>
      {/* A placeholder, not the last board: after a drop that board may be stale or mid-update. */}
      <div className="connection-lost-backdrop" aria-hidden="true" />
      {/* Escape has no dismiss action here (only "New Game" clears this state), so cancel is suppressed. */}
      <dialog
        className="modal connection-lost"
        ref={dialogRef}
        aria-labelledby="connection-lost-title"
        onCancel={(e) => e.preventDefault()}
      >
        <p className="reason">Connection lost</p>
        <h2 id="connection-lost-title">{outOfDate ? 'This page is out of date' : "This game can't be resumed"}</h2>
        <p className="body">{body}</p>
        <div className="actions">
          <button className="btn primary" onClick={outOfDate ? onReload : onNewGame} autoFocus>
            {outOfDate ? 'Reload Page' : 'New Game'}
          </button>
        </div>
      </dialog>
    </>
  )
}
