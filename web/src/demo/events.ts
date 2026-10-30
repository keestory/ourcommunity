import type { EventItem, Growth } from '../lib/types'
import { DemoError, person, staff, type DemoEvent, type DemoState } from './model'
export function notify(s: DemoState, recipient: string, title: string, eventId: number | null) {
  if (s.preferences[recipient]?.muted) return
  s.notifications.push({ id: s.nextId++, recipient, group_id: 'hangang', kind: 'demo', title, event_id: eventId, read: false, created_at: new Date().toISOString() })
  s.notifications = s.notifications.slice(-100)
}
export function audit(s: DemoState, detail: string, objectId: number | string) {
  s.audits.unshift({ action: 'demo', object_id: String(objectId), detail, actor_name: person(s.persona!).display_name, created_at: new Date().toISOString() }); s.audits = s.audits.slice(0, 100)
}
function promote(s: DemoState, e: DemoEvent) {
  if (e.status === 'cancelled' || Date.parse(e.starts_at) <= Date.now()) return
  for (const a of e.attendees) if (a.status === 'offered' && Date.parse(a.offer_expires_at!) <= Date.now()) a.status = 'expired'
  while (e.attendees.filter(a => ['confirmed', 'offered'].includes(a.status)).length < e.capacity) {
    const next = e.attendees.find(a => a.status === 'waitlisted'); if (!next) break
    next.status = 'offered'; next.offer_expires_at = new Date(Math.min(Date.now() + 1800000, Date.parse(e.starts_at))).toISOString()
    notify(s, next.user_id, '시연 모임에 빈자리가 생겼어요.', e.id)
  }
}
export function eventView(s: DemoState, e: DemoEvent): EventItem {
  promote(s, e)
  const mine = e.attendees.find(a => a.user_id === s.persona)
  return { ...e, group_id: 'hangang', confirmed_count: e.attendees.filter(a => a.status === 'confirmed').length, offered_count: e.attendees.filter(a => a.status === 'offered').length, waiting_count: e.attendees.filter(a => a.status === 'waitlisted').length, my_status: mine?.status as EventItem['my_status'] ?? null, my_attendance: mine?.attendance ?? null, offer_expires_at: mine?.offer_expires_at ?? null, can_mark_attendance: staff(s.persona) && e.status === 'published' && Date.parse(e.starts_at) <= Date.now(), attendees: staff(s.persona) ? e.attendees : undefined }
}
export function eventAction(s: DemoState, e: DemoEvent, action: string, body: Record<string, unknown>) {
  const user = s.persona!
  promote(s, e)
  if (e.status !== 'published') throw new DemoError('취소된 모임이에요.')
  if (action === 'rsvp') {
    if (Date.parse(e.starts_at) <= Date.now()) throw new DemoError('이미 시작한 모임이에요.')
    let mine = e.attendees.find(a => a.user_id === user)
    if (body.action === 'cancel') { if (mine) { mine.status = 'cancelled'; mine.attendance = 'unmarked' }; promote(s, e) }
    else if (body.action === 'accept') { if (mine?.status !== 'offered') throw new DemoError('빈자리 제안이 만료됐어요. 다시 신청해 주세요.'); mine.status = 'confirmed' }
    else if (body.action === 'join') {
      if (!mine || !['confirmed', 'offered', 'waitlisted'].includes(mine.status)) {
        if (mine) e.attendees = e.attendees.filter(a => a !== mine)
        mine = { user_id: user, display_name: person(user).display_name, color: person(user).color, status: e.attendees.filter(a => ['confirmed', 'offered'].includes(a.status)).length < e.capacity ? 'confirmed' : 'waitlisted', attendance: 'unmarked' }; e.attendees.push(mine)
      }
    } else throw new DemoError('신청 방법을 확인해 주세요.')
  } else {
    if (!staff(user)) throw new DemoError('운영자 역할에서 할 수 있어요.', 403)
    if (action === 'attendance') {
      const a = e.attendees.find(a => a.user_id === body.user_id)
      if (Date.parse(e.starts_at) > Date.now() || !a || a.status !== 'confirmed' || a.user_id === user) throw new DemoError('시작한 모임의 다른 참가자 출석만 확인할 수 있어요.')
      if (body.present && !s.members.includes(a.user_id)) throw new DemoError('현재 크루 멤버의 출석만 새로 확인할 수 있어요. 기존 출석의 정정은 가능해요.')
      a.attendance = body.present ? 'present' : 'unmarked'; audit(s, `${a.display_name} 출석 ${body.present ? '확인' : '수정'} · 시연`, e.id)
    } else if (action === 'cancel') {
      if (body.version !== e.version || Date.parse(e.starts_at) <= Date.now()) throw new DemoError('모임 상태가 바뀌었어요. 새로고침 후 확인해 주세요.', 409)
      e.status = 'cancelled'; e.version++
      e.attendees.forEach(a => { a.status = 'cancelled'; a.attendance = 'unmarked'; notify(s, a.user_id, '시연 모임이 취소됐어요.', e.id) }); audit(s, '모임 취소 · 시연', e.id)
    } else throw new DemoError('지원하지 않는 체험 동작이에요.', 404)
  }
  return eventView(s, e)
}
export function growth(s: DemoState): Growth {
  const count = s.events.filter(e => e.status === 'published').reduce((n, e) => n + e.attendees.filter(a => a.attendance === 'present' && a.status === 'confirmed').length, 0)
  return { total_contributions: count, rule: '시연 모임의 출석을 확인하면 공동 기념물이 생겨요. 메시지 수와 운동량은 보상하지 않고, 쉬어도 기록은 줄지 않아요.', recent: { visible: false, stage: 'quiet', label: '잔잔한 우리 공간 · 활기는 시연 집계에서 숨겨요', period: '실제 회원 활동 집계 없음' }, assets: [
    { id: 'trail-sign', name: '우리의 첫 이정표', description: '처음 함께 달린 날의 작은 표시.', goal: 1 },
    { id: 'bench', name: '잠깐 쉬어 가는 벤치', description: '함께한 이야기가 쉬어 가는 자리.', goal: 3 },
    { id: 'memory-tree', name: '함께 자라는 기억나무', description: '서로의 시간을 기억하는 나무.', goal: 6 },
  ].map(a => ({ ...a, progress: Math.min(count, a.goal), unlocked: count >= a.goal })) }
}
