import { useEffect, useRef } from 'react'

export function useAutoOpenDialog<T extends HTMLDialogElement>() {
  const ref = useRef<T>(null)
  useEffect(() => {
    ref.current?.showModal()
  }, [])
  return ref
}
