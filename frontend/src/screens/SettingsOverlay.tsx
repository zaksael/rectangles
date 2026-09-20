interface SettingsOverlayProps {
  onClose: () => void
}

export function SettingsOverlay({ onClose }: SettingsOverlayProps) {
  return (
    <div>
      <p>Settings</p>
      <button onClick={onClose}>Close</button>
    </div>
  )
}
