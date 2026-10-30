export const day = (value: string) => new Intl.DateTimeFormat('ko-KR', { timeZone: 'Asia/Seoul', month: 'long', day: 'numeric', weekday: 'short' }).format(new Date(value))
export const clock = (value: string) => new Intl.DateTimeFormat('ko-KR', { timeZone: 'Asia/Seoul', hour: 'numeric', minute: '2-digit' }).format(new Date(value))
export const fullDate = (value: string) => `${day(value)} ${clock(value)}`
export const fromKst = (value: string) => new Date(`${value}:00+09:00`).toISOString()
export function futureLocal(hours = 24) { const date = new Date(Date.now() + (hours + 9) * 3600000); return date.toISOString().slice(0, 16) }
export const statusLabel: Record<string, string> = { confirmed: '참가 확정', waitlisted: '대기 중', offered: '빈자리 제안', cancelled: '취소됨', expired: '제안 만료', present: '출석', absent: '불참', unmarked: '확인 전' }
export function safeNext(value: string | null) { return value?.startsWith('/') && !value.startsWith('//') && !value.includes('\\') && !value.startsWith('/auth') ? value : '/' }
