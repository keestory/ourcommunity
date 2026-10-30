import type { Announcement, Attendance, Group, Message, NotificationItem, User } from '../lib/types'
export type DemoEvent = { id: number; title: string; description: string; location: string; starts_at: string; ends_at: string; capacity: number; status: 'published' | 'cancelled'; version: number; attendees: (Attendance & { offer_expires_at?: string })[] }
export type DemoState = {
  space_layout?: Group['space_layout'];
  version: 1; persona: string | null; nextId: number; palette: Group['palette']; groupVersion: number;
  members: string[]; preferences: Record<string, Group['preferences']>; messages: Message[];
  announcements: Announcement[]; events: DemoEvent[]; blocks: Record<string, string[]>;
  notifications: (NotificationItem & { recipient: string })[]; commands: Record<string, number>;
  reports: { id: number; message_id: number; reason: string; status: string; created_at: string; reporter: string; subject: string }[];
  audits: { action: string; object_id: string; detail: string; actor_name: string; created_at: string }[];
}
export const people: User[] = [
  { id: 'sora', username: 'sora', display_name: '소라', color: '#52786B' },
  { id: 'mira', username: 'mira', display_name: '미라', color: '#AC603D' },
  { id: 'jiho', username: 'jiho', display_name: '지호', color: '#687E94' },
  { id: 'jun', username: 'jun', display_name: '준', color: '#87739A' },
  { id: 'hana', username: 'hana', display_name: '하나', color: '#8A704E' },
]
export const person = (id: string) => people.find(p => p.id === id)!
export const staff = (id: string | null) => id === 'mira'
export function seed(): DemoState {
  const now = Date.now(), time = (hours: number) => new Date(now + hours * 3600000).toISOString()
  const attendees = (ids: string[], present = false): Attendance[] => ids.map(id => ({ user_id: id, display_name: person(id).display_name, color: person(id).color, status: 'confirmed', attendance: present ? 'present' : 'unmarked' }))
  return { version: 1, persona: null, nextId: 100, palette: 'dawn', groupVersion: 1, members: people.map(p => p.id), preferences: {}, blocks: {}, commands: {}, reports: [], audits: [], notifications: [],
    messages: [
      { id: 1, seq: 1, client_id: 'sample-1', body: '다음 모임은 강바람 따라 천천히 달려요. 처음 오셔도 괜찮아요 🌿', author: person('mira'), created_at: time(-2), deleted: false, mine: false },
      { id: 2, seq: 2, client_id: 'sample-2', body: '좋아요! 달리기 끝나고 벤치에서 같이 쉬어요.', author: person('jiho'), created_at: time(-1), deleted: false, mine: false },
    ],
    announcements: [{ id: 3, body: '가상 크루 체험에 오신 걸 환영해요. 멤버로 모임을 신청하고, 운영자로 바꿔 지난 모임의 지호 출석을 확인해 보세요. 우리 공간에 벤치가 생겨요.', author_name: '미라', created_at: time(-3) }],
    events: [
      { id: 3, title: '함께 쉬는 저녁 · 대기 체험', description: '정원이 찬 시연 모임이에요. 대기 신청과 빈자리 제안을 체험할 수 있어요.', location: '강가 벤치 · 시연 장소', starts_at: time(72), ends_at: time(73), capacity: 2, status: 'published', version: 1, attendees: attendees(['mira', 'jiho']) },
      { id: 1, title: '이번 주, 강바람 한 바퀴', description: '가상의 모임이에요. 거리나 속도보다 함께하는 시간을 즐겨요.', location: '망원 한강공원 시계탑 앞 · 시연 장소', starts_at: time(48), ends_at: time(49), capacity: 3, status: 'published', version: 1, attendees: attendees(['mira', 'jiho']) },
      { id: 2, title: '지난 모임 · 함께한 아침', description: '운영자로 지호의 출석을 확인하면 세 번째 공동 참여가 되어 벤치가 생겨요.', location: '한강 산책길 · 시연 장소', starts_at: time(-26), ends_at: time(-25), capacity: 8, status: 'published', version: 1, attendees: [...attendees(['sora', 'hana'], true), ...attendees(['jiho', 'mira'])] },
    ],
  }
}
export class DemoError extends Error { constructor(message: string, public status = 400) { super(message) } }
export function validate(value: unknown): asserts value is DemoState {
  const s = value as DemoState
  if (!s || s.version !== 1 || !Number.isInteger(s.nextId) || !Array.isArray(s.members) || !Array.isArray(s.messages) || !Array.isArray(s.events) || !Array.isArray(s.announcements) || !Array.isArray(s.reports) || !Array.isArray(s.audits) || !Array.isArray(s.notifications) || !s.preferences || !s.blocks || !s.commands || (s.persona !== null && !people.some(p => p.id === s.persona))) throw new DemoError('이 브라우저의 체험 기록을 읽을 수 없어요. 체험 초기화로 샘플을 다시 시작할 수 있어요.')
}
