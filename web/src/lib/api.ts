let csrf: string | null = null
export function setCsrf(value: string | null) { csrf = value }
export class ApiError extends Error {
  status: number
  fields: { field: string; message: string }[]
  constructor(message: string, status = 0, fields: { field: string; message: string }[] = []) { super(message); this.status = status; this.fields = fields }
}
export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  let response: Response
  try {
    const timeout = AbortSignal.timeout(15000)
    const signal = options.signal ? AbortSignal.any([options.signal, timeout]) : timeout
    response = await fetch(`/api${path}`, { credentials: 'same-origin', ...options, signal, headers: { 'Content-Type': 'application/json', ...(csrf ? { 'X-CSRF-Token': csrf } : {}), ...options.headers } })
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') throw error
    throw new ApiError('연결이 잠시 끊겼어요. 입력은 그대로 두었으니 다시 시도해 주세요.')
  }
  const payload = await response.json().catch(() => ({}))
  if (!response.ok) {
    if (response.status === 401 && path !== '/session' && !path.startsWith('/auth/')) window.dispatchEvent(new Event('session-expired'))
    if (response.status === 403) window.dispatchEvent(new CustomEvent('access-check', { detail: path }))
    throw new ApiError(typeof payload.detail === 'string' ? payload.detail : '요청을 처리하지 못했어요. 다시 확인해 주세요.', response.status, payload.fields)
  }
  return payload as T
}
export function mutate<T>(path: string, body?: unknown, method = 'POST') { return api<T>(path, { method, ...(body === undefined ? {} : { body: JSON.stringify(body) }) }) }
export function errorText(error: unknown) { return error instanceof Error ? error.message : '잠시 후 다시 시도해 주세요.' }
export function requestId() { return crypto.randomUUID() }
