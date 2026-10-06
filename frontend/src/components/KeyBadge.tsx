// The key hint chip shown only while Shift is held (see useShiftHeld); the button's aria-keyshortcuts already names the key.
export function KeyBadge({ children }: { children: string }) {
  return (
    <kbd className="key-badge" aria-hidden="true">
      {children}
    </kbd>
  )
}
