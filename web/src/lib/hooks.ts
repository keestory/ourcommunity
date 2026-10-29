import { useCallback, useEffect, useRef, useState } from 'react'
import { api, ApiError, errorText } from './api'
export function useResource<T>(path: string | null, poll = false) {
  const [state, setState] = useState<{ path: string | null; data?: T; error: string; status: number; loading: boolean }>({ path, error: '', status: 0, loading: true })
  const [revision, setRevision] = useState(0)
  const refresh = useCallback(() => setRevision(value => value + 1), [])
  useEffect(() => {
    if (!path) return
    let alive = true
    let controller: AbortController | null = null
    let inFlight = false
    let denied = false
    const read = async () => {
      if (inFlight || denied || document.visibilityState === 'hidden') return
      inFlight = true; controller = new AbortController()
      try { const data = await api<T>(path, { signal: controller.signal }); if (alive) setState({ path, data, error: '', status: 0, loading: false }) }
      catch (error) {
        if (alive && !(error instanceof DOMException && error.name === 'AbortError')) {
          const status = error instanceof ApiError ? error.status : 0
          denied = [401, 403, 404].includes(status)
          setState(previous => ({ path, data: [401, 403, 404].includes(status) ? undefined : previous.path === path ? previous.data : undefined, error: errorText(error), status, loading: false }))
        }
      } finally { inFlight = false }
    }
    void read()
    const timer = poll ? setInterval(() => void read(), 3000) : null
    const visible = () => { if (document.visibilityState === 'visible') void read() }
    window.addEventListener('online', visible); document.addEventListener('visibilitychange', visible)
    return () => { alive = false; controller?.abort(); if (timer) clearInterval(timer); window.removeEventListener('online', visible); document.removeEventListener('visibilitychange', visible) }
  }, [path, poll, revision])
  const current = state.path === path ? state : { path, error: '', status: 0, loading: true, data: undefined }
  return { ...current, refresh }
}
export function useTitle(title: string) { useEffect(() => { document.title = `${title} · ourcommunity` }, [title]) }
export function useMutation() {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const lock = useRef(false)
  const run = async (work: () => Promise<void>) => {
    if (lock.current) return
    lock.current = true; setBusy(true); setError('')
    try { await work() } catch (failure) { setError(errorText(failure)) }
    finally { lock.current = false; setBusy(false) }
  }
  return { busy, error, setError, run }
}
