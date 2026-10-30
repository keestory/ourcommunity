import { DemoError, people, person, staff, type DemoEvent, type DemoState } from './model'
import { audit, eventAction, eventView, growth, notify } from './events'
import { persistentStorage, transact } from './storage'
import type { Group, MessagePage, Session } from '../lib/types'
function text(value: unknown, max = 2000) { if (typeof value !== 'string' || !value.trim() || value.trim().length > max) throw new DemoError('입력 내용과 길이를 확인해 주세요.'); return value.trim() }
function operator(s: DemoState) { if (!staff(s.persona)) throw new DemoError('운영자 역할에서 할 수 있어요.', 403) }
function group(s: DemoState): Group { return { space_layout: s.space_layout, id: 'hangang', name: '한강 새벽 러너스', description: '각자의 속도로 달리고, 같은 마음으로 쉬어요.', subtitle: '강바람 따라, 함께 쌓이는 아침', role: staff(s.persona) ? 'owner' : 'member', member_count: s.members.length, public_space: false, palette: s.palette, version: s.groupVersion, preferences: s.preferences[s.persona!] ?? { muted: false, activity_consent: false } } }
function dispatch(s: DemoState, path: string, method: string, body: Record<string, unknown>) {
  const url = new URL(path, 'https://browser-demo.invalid'), parts = url.pathname.split('/').filter(Boolean), id = s.persona
  if (path === '/session') return { user: id ? person(id) : null, csrf: null, demo: true, preview: { enabled: true, isolated: true, persistent: persistentStorage(), restart_resets: false, storage: 'browser', expires_at: null, ttl_seconds: 0, mutation_limit: 0, sharing_enabled: false } } satisfies Session
  if (path === '/auth/demo' && method === 'POST') {
    if (!['sora', 'mira'].includes(String(body.persona))) throw new DemoError('체험 역할을 다시 선택해 주세요.')
    if (!s.members.includes(String(body.persona))) throw new DemoError('이 역할은 크루를 떠났어요. 체험 초기화로 다시 시작할 수 있어요.')
    s.persona = String(body.persona); return { ok: true }
  }
  if (path === '/auth/logout' && method === 'POST') { s.persona = null; return { ok: true } }
  if (parts[0] === 'public' || parts[0] === 'invites') throw new DemoError('브라우저 체험은 공개 공유와 다른 방문자 초대를 지원하지 않아요.', 404)
  if (!id) throw new DemoError('가상 역할을 먼저 선택해 주세요.', 401)
  if (!s.members.includes(id)) throw new DemoError('이 가상 역할은 크루를 떠났어요. 체험을 초기화해 다시 시작할 수 있어요.', 403)
  if (parts[0] === 'groups' && parts.length === 1 && method === 'GET') return { items: [group(s)] }
  if (parts[0] === 'notifications') {
    if (parts[1] === 'read' && method === 'POST') s.notifications.filter(n => n.recipient === id).forEach(n => { n.read = true })
    return { items: s.notifications.filter(n => n.recipient === id).slice().reverse() }
  }
  if (parts[0] === 'blocks') {
    if (method === 'DELETE') s.blocks[id] = (s.blocks[id] ?? []).filter(p => p !== parts[1])
    return { items: (s.blocks[id] ?? []).map(person) }
  }
  if (parts[0] === 'messages' && method === 'DELETE') {
    const m = s.messages.find(m => m.id === +parts[1]); if (!m) throw new DemoError('메시지가 없어요.', 404)
    if (m.author.id !== id && !staff(id)) throw new DemoError('이 메시지를 삭제할 수 없어요.', 403)
    m.deleted = true; m.body = ''; audit(s, '메시지 삭제 · 시연', m.id); return { ok: true }
  }
  if (parts[0] === 'reports' && method === 'PATCH') {
    operator(s); const r = s.reports.find(r => r.id === +parts[1] && r.subject !== id)
    if (!r) throw new DemoError('검토할 신고가 없어요.', 404)
    r.status = 'reviewed'; audit(s, '신고 검토 · 브라우저 시연만', r.id); return { ok: true }
  }
  if (parts[0] === 'events') {
    const e = s.events.find(e => e.id === +parts[1]); if (!e) throw new DemoError('모임을 찾을 수 없어요.', 404)
    return parts.length === 2 && method === 'GET' ? eventView(s, e) : eventAction(s, e, parts[2], body)
  }
  if (parts[0] !== 'groups' || parts[1] !== 'hangang') throw new DemoError('이 체험 공간에 접근할 수 없어요.', 403)
  if (parts.length === 2 && method === 'GET') return group(s)
  switch (parts[2]) {
    case 'growth': return growth(s)
    case 'space': {
      if (method !== 'PATCH') throw new DemoError('지원하지 않는 공간 요청이에요.', 405)
      operator(s)
      const asset = growth(s).assets.find(a => a.id === body.asset_id)
      if (!asset?.unlocked) throw new DemoError('함께 만든 기념물만 배치할 수 있어요.', 403)
      if (body.version !== s.groupVersion) throw new DemoError('다른 탭에서 공간이 바뀌었어요. 새로고침 후 다시 선택해 주세요.', 409)
      if (!['entry', 'center', 'garden'].includes(String(body.slot))) throw new DemoError('배치할 자리를 선택해 주세요.')
      const layout = { 'trail-sign': 'entry', bench: 'center', 'memory-tree': 'garden', ...s.space_layout } as NonNullable<Group['space_layout']>
      const slot = body.slot as typeof layout[string], previous = layout[asset.id]
      const occupied = Object.keys(layout).find(key => key !== asset.id && layout[key] === slot)
      if (occupied) layout[occupied] = previous
      layout[asset.id] = slot; s.space_layout = layout; s.groupVersion++
      audit(s, `${asset.name} 배치 변경 · 시연`, asset.id); return group(s)
    }
    case 'members':
      if (method === 'DELETE') {
        operator(s); if (parts[3] === 'mira') throw new DemoError('소유자는 내보낼 수 없어요.')
        s.members = s.members.filter(p => p !== parts[3]); cancelFuture(s, parts[3]); audit(s, `${person(parts[3])?.display_name ?? '멤버'} 내보내기 · 시연`, parts[3])
      }
      return { items: people.filter(p => s.members.includes(p.id)).map(p => ({ ...p, role: staff(p.id) ? 'owner' : 'member' })) }
    case 'read': return { ok: true }
    case 'messages': {
      if (method === 'POST') {
        const bodyText = text(body.body), key = text(body.client_id, 100)
        const prior = s.messages.find(m => m.client_id === key && m.author.id === id)
        if (prior) { if (prior.body !== bodyText) throw new DemoError('이미 처리한 메시지예요.', 409); return { ...prior, mine: true } }
        if (s.messages.length >= 500) throw new DemoError('시연 메시지 500개를 채웠어요. 체험 초기화 후 다시 시작할 수 있어요.')
        const next = s.nextId++, m = { id: next, seq: next, client_id: key, body: bodyText, author: person(id), created_at: new Date().toISOString(), deleted: false, mine: true }
        s.messages.push(m); return m
      }
      const visible = s.messages.filter(m => !(s.blocks[id] ?? []).includes(m.author.id) && !(s.blocks[m.author.id] ?? []).includes(id))
      const before = +(url.searchParams.get('before') ?? Infinity), all = visible.filter(m => m.seq < before), items = all.slice(-50).map(m => ({ ...m, mine: m.author.id === id }))
      return { items, has_more: all.length > 50, next_cursor: items.at(-1)?.seq ?? 0, read_seq: 0, unread_count: 0 } satisfies MessagePage
    }
    case 'announcements':
      if (method === 'POST') {
        operator(s); const key = `announcement:${id}:${text(body.request_id, 100)}`
        if (!s.commands[key]) {
          const item = { id: s.nextId++, body: text(body.body), author_name: person(id).display_name, created_at: new Date().toISOString() }
          s.announcements.unshift(item); s.announcements = s.announcements.slice(0, 50); s.commands[key] = item.id
          s.members.filter(p => p !== id).forEach(p => notify(s, p, '새 시연 공지가 올라왔어요.', null))
        }
      }
      return { items: s.announcements }
    case 'events':
      if (method === 'POST') {
        operator(s); const key = `event:${id}:${text(body.request_id, 100)}`
        if (s.commands[key]) return eventView(s, s.events.find(e => e.id === s.commands[key])!)
        const start = text(body.starts_at, 50), end = text(body.ends_at, 50), capacity = Number(body.capacity)
        if (!Number.isFinite(Date.parse(start)) || !Number.isFinite(Date.parse(end)) || Date.parse(start) <= Date.now() || Date.parse(end) <= Date.parse(start) || Date.parse(end) - Date.parse(start) > 86400000 || !Number.isInteger(capacity) || capacity < 2 || capacity > 100) throw new DemoError('모임 시간과 정원을 확인해 주세요.')
        if (s.events.length >= 60) throw new DemoError('시연 모임 60개를 채웠어요. 체험 초기화 후 다시 시작할 수 있어요.')
        const e: DemoEvent = { id: s.nextId++, title: text(body.title, 80), description: String(body.description ?? '').slice(0, 1000), location: text(body.location, 120), starts_at: start, ends_at: end, capacity, status: 'published', version: 1, attendees: [] }
        s.events.push(e); s.commands[key] = e.id; audit(s, '모임 만들기 · 시연', e.id); return eventView(s, e)
      }
      return { items: s.events.map(e => eventView(s, e)) }
    case 'settings':
      operator(s)
      if (body.public_space !== undefined) throw new DemoError('브라우저 체험은 외부 공개를 지원하지 않아요.')
      if (body.version !== s.groupVersion) throw new DemoError('다른 탭에서 설정이 바뀌었어요. 새로고침 후 다시 선택해 주세요.', 409)
      if (!['dawn', 'forest', 'sunset'].includes(String(body.palette))) throw new DemoError('풍경 색감을 선택해 주세요.')
      s.palette = body.palette as Group['palette']; s.groupVersion++; return group(s)
    case 'preferences': {
      const p = s.preferences[id] ?? { muted: false, activity_consent: false }
      if (typeof body.muted === 'boolean') p.muted = body.muted
      if (typeof body.activity_consent === 'boolean') throw new DemoError('브라우저 체험에는 실제 활동 집계가 연결되지 않았어요.')
      s.preferences[id] = p; return group(s)
    }
    case 'blocks': {
      if (!person(parts[3]) || parts[3] === id) throw new DemoError('차단할 멤버를 확인해 주세요.')
      s.blocks[id] = [...new Set([...(s.blocks[id] ?? []), parts[3]])]; return { ok: true }
    }
    case 'reports':
      if (method === 'POST') {
        const m = s.messages.find(m => m.id === body.message_id); if (!m || m.author.id === id) throw new DemoError('신고할 메시지를 확인해 주세요.')
        s.reports.push({ id: s.nextId++, message_id: m.id, reason: text(body.reason, 300), status: 'open', created_at: new Date().toISOString(), reporter: id, subject: m.author.id }); return { ok: true }
      }
      operator(s); return { items: s.reports.filter(r => r.subject !== id) }
    case 'audit': operator(s); return { items: s.audits }
    case 'leave':
      if (staff(id)) throw new DemoError('체험 소유자는 크루를 떠날 수 없어요.')
      s.members = s.members.filter(p => p !== id); cancelFuture(s, id); s.persona = null; return { ok: true }
    default: throw new DemoError('이 기능은 브라우저 체험에 연결되지 않았어요.', 404)
  }
}
function cancelFuture(s: DemoState, id: string) {
  s.events.filter(e => Date.parse(e.starts_at) > Date.now()).forEach(e => { const a = e.attendees.find(a => a.user_id === id); if (a) { a.status = 'cancelled'; a.attendance = 'unmarked' }; eventView(s, e) })
}
export async function demoApi<T>(path: string, options: RequestInit): Promise<T> {
  options.signal?.throwIfAborted()
  return transact(s => { options.signal?.throwIfAborted(); return dispatch(s, path, options.method ?? 'GET', typeof options.body === 'string' ? JSON.parse(options.body) : {}) as T })
}
