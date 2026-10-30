import { useRef } from 'react'
import { Link } from 'react-router-dom'
import { ArrowUpRight, Check, MapPin } from 'lucide-react'
import { Button, ErrorState } from './ui'
import { mutate, requestId } from '../lib/api'
import { fullDate, statusLabel } from '../lib/format'
import { useMutation } from '../lib/hooks'
import type { EventItem } from '../lib/types'
export function MeetingAction({ event, refresh }: { event: EventItem; refresh: () => void }) {
  const action = useMutation(), key = useRef(requestId()), active = ['confirmed', 'waitlisted', 'offered'].includes(event.my_status || '')
  return <section className="home-meeting"><div className="section-heading"><h2>다음 모임</h2><Link to={`/groups/${event.group_id}/events`} className="text-link">모두 보기 <ArrowUpRight size={16}/></Link></div><time dateTime={event.starts_at}>{fullDate(event.starts_at)}</time><Link className="meeting-title" to={`/groups/${event.group_id}/events/${event.id}`}>{event.title}</Link><p><MapPin size={16}/>{event.location}</p><div className="meeting-action-row"><span>{event.confirmed_count}/{event.capacity}명 참가{active && <strong><Check size={14}/>{statusLabel[event.my_status!]}</strong>}</span>{active ? <Link className="button secondary" to={`/groups/${event.group_id}/events/${event.id}`}>신청 확인 <ArrowUpRight size={16}/></Link> : <Button busy={action.busy} onClick={() => void action.run(async () => { await mutate(`/events/${event.id}/rsvp`, { action: 'join', request_id: key.current }); key.current = requestId(); refresh() })}>{event.confirmed_count + event.offered_count >= event.capacity ? '대기 신청' : '참가 신청'}</Button>}</div>{action.error && <ErrorState compact message={action.error}/>}</section>
}
