import { createContext, useCallback, useContext, useEffect, useRef, useState, type ReactNode } from 'react'
import { api, ApiError, errorText, mutate, setCsrf } from './api'
import type { Session } from './types'
const EMPTY: Session = { user: null, csrf: null, demo: false }
const Context = createContext<{ session: Session; loading: boolean; error: string; refresh: () => Promise<void>; login: (mode: string, data: unknown) => Promise<void>; logout: () => Promise<void> } | null>(null)
export function SessionProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<Session>(EMPTY)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const generation = useRef(0)
  const pending = useRef<AbortController | null>(null)
  const invalidate = useCallback(() => { generation.current += 1; pending.current?.abort(); pending.current = null }, [])
  const refresh = useCallback(async () => {
    invalidate()
    const current = generation.current
    const controller = new AbortController(); pending.current = controller
    try { const value = await api<Session>('/session', { signal: controller.signal }).catch(error => { if (error instanceof ApiError && error.status === 401) return api<Session>('/session', { signal: controller.signal }); throw error }); if (current !== generation.current) return; setCsrf(value.csrf); setSession(value); setError('') }
    catch (failure) { if (current === generation.current && !controller.signal.aborted) setError(errorText(failure)) }
    finally { if (current === generation.current) setLoading(false) }
  }, [invalidate])
  useEffect(() => { void refresh(); return invalidate }, [refresh, invalidate])
  useEffect(() => {
    const clear = () => { invalidate(); setCsrf(null); setSession(current => ({ ...current, user: null, csrf: null })); setLoading(false) }
    const channel = new BroadcastChannel('ourcommunity-session')
    channel.onmessage = clear
    window.addEventListener('session-expired', clear)
    return () => { channel.close(); window.removeEventListener('session-expired', clear) }
  }, [invalidate])
  const login = async (mode: string, data: unknown) => { invalidate(); await mutate(`/auth/${mode}`, data); await refresh() }
  const logout = async () => {
    invalidate(); await mutate('/auth/logout'); setCsrf(null); setSession(current => ({ ...current, user: null, csrf: null }))
    const channel = new BroadcastChannel('ourcommunity-session'); channel.postMessage('logout'); channel.close()
  }
  return <Context.Provider value={{ session, loading, error, refresh, login, logout }}>{children}</Context.Provider>
}
export function useSession() { const value = useContext(Context); if (!value) throw new Error('SessionProvider missing'); return value }
