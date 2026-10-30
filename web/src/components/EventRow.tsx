import { ArrowUpRight, MapPin } from 'lucide-react'
import { Link } from 'react-router-dom'
import type { EventItem } from '../lib/types'
import { clock, day, statusLabel } from '../lib/format'
export function EventRow({ event }: { event: EventItem }) {
  const date = new Date(event.starts_at)
  return <Link to={`/groups/${event.group_id}/events/${event.id}`} className={`event-row ${event.status === 'cancelled' ? 'cancelled' : ''}`}><div className="date-tile"><small>{new Intl.DateTimeFormat('ko-KR', { timeZone: 'Asia/Seoul', month: 'short' }).format(date)}</small><strong>{new Intl.DateTimeFormat('ko-KR', { timeZone: 'Asia/Seoul', day: 'numeric' }).format(date).replace('일', '')}</strong></div><div className="event-row-body"><span className="eyebrow">{day(event.starts_at)} · {clock(event.starts_at)}</span><h3>{event.title}</h3><p><MapPin size={14}/>{event.location}</p><span className="event-meta">{event.status === 'cancelled' ? '취소된 모임' : `${event.confirmed_count} / ${event.capacity}명 참가`}{event.my_status && <span className="small-tag">{statusLabel[event.my_status]}</span>}</span></div><ArrowUpRight size={21} className="row-arrow"/></Link>
}
