import { DemoError, seed, validate, type DemoState } from './model'
export const BROWSER_DEMO = import.meta.env.VITE_BROWSER_DEMO === '1'
export const DATABASE = 'ourcommunity-browser-demo-v1'
let database: Promise<IDBDatabase | null> | undefined
let memory: DemoState | undefined
let notice = ''
let persistent = true
const listeners = new Set<() => void>()
export const storageNotice = () => notice
export const subscribeStorage = (listener: () => void) => { listeners.add(listener); return () => { listeners.delete(listener) } }
function announce(value: string) { notice = value; listeners.forEach(listener => listener()) }
function open(): Promise<IDBDatabase | null> {
  if (!database) database = new Promise<IDBDatabase | null>(resolve => {
    let settled = false
    const finish = (db: IDBDatabase | null) => {
      if (settled) { db?.close(); return }
      settled = true; clearTimeout(timer)
      if (!db) { persistent = false; announce('브라우저 저장소를 사용할 수 없어 이번 화면에서만 체험해요. 새로고침하거나 닫으면 변경 내용이 사라져요.') }
      resolve(db)
    }
    const timer = setTimeout(() => finish(null), 3000)
    try {
      const request = indexedDB.open(DATABASE, 1)
      request.onupgradeneeded = () => request.result.createObjectStore('demo')
      request.onsuccess = () => finish(request.result)
      request.onerror = () => finish(null)
      request.onblocked = () => finish(null)
    } catch { finish(null) }
  })
  return database
}
// One read/write transaction serializes all tabs; UI success waits for commit.
export async function transact<T>(work: (state: DemoState) => T, reset = false): Promise<T> {
  const db = await open()
  if (!db) {
    const next = structuredClone(reset ? seed() : memory ?? seed())
    const result = work(next); memory = next; return structuredClone(result)
  }
  return new Promise<T>((resolve, reject) => {
    let result: T, failure: unknown
    const tx = db.transaction('demo', 'readwrite'), store = tx.objectStore('demo'), request = store.get('state')
    request.onsuccess = () => {
      try {
        const state: unknown = reset || request.result === undefined ? seed() : request.result
        validate(state); result = work(state)
        if (JSON.stringify(state).length > 1000000) throw new DemoError('체험 기록이 가득 찼어요. 필요한 내용을 확인한 뒤 체험 초기화를 해주세요.')
        store.put(state, 'state')
      } catch (error) {
        failure = error instanceof DemoError || (error instanceof DOMException && error.name === 'AbortError') ? error : new DemoError('저장하지 못했어요. 입력은 그대로 두었으니 저장 공간을 확인하고 다시 시도해 주세요.')
        tx.abort()
      }
    }
    tx.oncomplete = () => { announce(''); resolve(structuredClone(result)) }
    tx.onabort = () => {
      if (!failure) announce('브라우저에 저장하지 못했어요. 입력은 유지돼요. 저장 공간을 확보한 뒤 다시 시도하거나 체험을 초기화해 주세요.')
      reject(failure ?? new DemoError('저장하지 못했어요. 입력은 그대로 두었으니 저장 공간을 확인하고 다시 시도해 주세요.'))
    }
  })
}
export async function resetDemo() { await transact(() => null, true) }
export const persistentStorage = () => persistent
