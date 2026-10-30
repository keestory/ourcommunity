import { createContext, useContext, useEffect, useId, useRef, useState, type ButtonHTMLAttributes, type ReactNode } from 'react'
import { AlertCircle, Check, LoaderCircle, X } from 'lucide-react'
import { useBlocker } from 'react-router-dom'
export function Button({ variant = 'primary', busy = false, className = '', children, disabled, ...props }: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: 'primary' | 'secondary' | 'ghost' | 'danger'; busy?: boolean }) {
  return <button type="button" {...props} className={`button ${variant} ${className}`} disabled={disabled || busy} aria-busy={busy || undefined}>{busy && <LoaderCircle size={17} className="spin" aria-hidden="true"/>}{children}</button>
}
export function Field({ label, name, hint, error, children }: { label: string; name: string; hint?: string; error?: string; children: ReactNode }) {
  return <div className="field"><label htmlFor={name}>{label}</label>{children}{hint && <small id={`${name}-help`}>{hint}</small>}{error && <p className="field-error" id={`${name}-error`}>{error}</p>}</div>
}
export function ErrorState({ message, retry, compact = false }: { message: string; retry?: () => void; compact?: boolean }) {
  return <div className={`error-state ${compact ? 'compact' : ''}`} role="alert"><AlertCircle size={20} aria-hidden="true"/><div><p>{message}</p>{retry && <Button variant="secondary" onClick={retry}>다시 시도</Button>}</div></div>
}
export function Loading({ label = '우리의 공간을 불러오고 있어요' }: { label?: string }) { return <div className="loading" role="status"><LoaderCircle size={24} className="spin" aria-hidden="true"/><p>{label}</p></div> }
export function EmptyState({ title, children }: { title: string; children?: ReactNode }) { return <div className="empty-state"><span className="empty-seed" aria-hidden="true">✳</span><h2>{title}</h2>{children}</div> }
export function Dialog({ open, title, children, onClose, busy = false }: { open: boolean; title: string; children: ReactNode; onClose: () => void; busy?: boolean }) {
  const ref = useRef<HTMLDialogElement>(null)
  const titleId = useId()
  useEffect(() => { const dialog = ref.current; if (!dialog) return; if (open && !dialog.open) dialog.showModal(); else if (!open && dialog.open) dialog.close() }, [open])
  return <dialog ref={ref} aria-labelledby={titleId} onCancel={event => { event.preventDefault(); if (!busy) onClose() }} className="dialog"><div className="dialog-heading"><h2 id={titleId}>{title}</h2><Button variant="ghost" className="icon-button" aria-label="창 닫기" onClick={onClose} disabled={busy} autoFocus><X size={20}/></Button></div>{children}</dialog>
}
export function Confirm({ open, title, children, confirmLabel, onConfirm, onClose, busy, error, danger = false }: { open: boolean; title: string; children: ReactNode; confirmLabel: string; onConfirm: () => void; onClose: () => void; busy?: boolean; error?: string; danger?: boolean }) {
  return <Dialog open={open} title={title} onClose={onClose} busy={busy}><div className="dialog-body">{children}</div>{error && <ErrorState compact message={error}/>}<div className="dialog-actions"><Button variant="secondary" onClick={onClose} disabled={busy}>돌아가기</Button><Button variant={danger ? 'danger' : 'primary'} busy={busy} onClick={onConfirm}>{confirmLabel}</Button></div></Dialog>
}
const ToastContext = createContext<(message: string) => void>(() => undefined)
export function ToastProvider({ children }: { children: ReactNode }) {
  const [message, setMessage] = useState('')
  useEffect(() => { if (!message) return; const timer = setTimeout(() => setMessage(''), 5000); return () => clearTimeout(timer) }, [message])
  return <ToastContext.Provider value={setMessage}>{children}<div className={`toast ${message ? 'visible' : ''}`} role="status" aria-live="polite">{message && <><Check size={18} aria-hidden="true"/>{message}<button aria-label="알림 닫기" onClick={() => setMessage('')}><X size={16}/></button></>}</div></ToastContext.Provider>
}
export const useToast = () => useContext(ToastContext)
export function DirtyGuard({ dirty, busy = false }: { dirty: boolean; busy?: boolean }) {
  const blocker = useBlocker(dirty)
  useEffect(() => { if (!dirty) return; const before = (event: BeforeUnloadEvent) => { event.preventDefault(); event.returnValue = '' }; window.addEventListener('beforeunload', before); return () => window.removeEventListener('beforeunload', before) }, [dirty])
  return <Confirm open={blocker.state === 'blocked'} title={busy ? '저장 결과를 확인하고 있어요' : '작성 중인 내용이 있어요'} confirmLabel={busy ? '저장 중' : '내용을 버리고 이동'} busy={busy} onClose={() => blocker.reset?.()} onConfirm={() => blocker.proceed?.()}><p>{busy ? '이미 보낸 요청의 결과를 기다린 뒤 이동할 수 있어요.' : '이 화면을 떠나면 아직 저장하지 않은 내용이 사라져요.'}</p></Confirm>
}
export function Avatar({ name, color, small = false }: { name: string; color?: string; small?: boolean }) { return <span aria-hidden="true" className={`avatar ${small ? 'small' : ''}`} style={{ borderColor: color }}>{name.slice(0, 1)}</span> }
export function focusInvalid(errors: Record<string, string>) { const key = Object.keys(errors)[0]; if (key) requestAnimationFrame(() => document.getElementById(key)?.focus()) }
