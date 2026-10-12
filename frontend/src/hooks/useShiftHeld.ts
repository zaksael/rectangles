import { useEffect } from 'react'

// Mirrors whether Shift is down as data-shift on the root, so the key badges can show in CSS alone.
export function useShiftHeld(): void {
  useEffect(() => {
    const root = document.documentElement
    function onKey(event: KeyboardEvent) {
      if (event.key === 'Shift') root.toggleAttribute('data-shift', event.type === 'keydown')
    }
    window.addEventListener('keydown', onKey)
    window.addEventListener('keyup', onKey)
    const onBlur = () => root.removeAttribute('data-shift')
    window.addEventListener('blur', onBlur)
    return () => {
      window.removeEventListener('keydown', onKey)
      window.removeEventListener('keyup', onKey)
      window.removeEventListener('blur', onBlur)
      root.removeAttribute('data-shift')
    }
  }, [])
}
