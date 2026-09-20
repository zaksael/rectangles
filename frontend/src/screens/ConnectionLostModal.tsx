interface ConnectionLostModalProps {
  isSeries: boolean
  onNewGame: () => void
}

export function ConnectionLostModal({ isSeries, onNewGame }: ConnectionLostModalProps) {
  const body = isSeries
    ? "The connection to the server dropped and couldn't be restored. Rejoining an in-progress game isn't supported yet, and the series can't be resumed either — you'll need to start a new one."
    : "The connection to the server dropped and couldn't be restored. Rejoining an in-progress game isn't supported yet — you'll need to start a new one."

  return (
    <div>
      <p>This game can&apos;t be resumed</p>
      <p>{body}</p>
      <button className="btn primary" onClick={onNewGame} autoFocus>
        New Game
      </button>
    </div>
  )
}
