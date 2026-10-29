import { useEffect, useRef, useState, type FormEvent } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { ArrowLeft, CalendarDays, Check, Clock3, MapPin, Plus, Users } from 'lucide-react'
import { useGroup } from '../components/Layout'
import { EventRow } from '../components/EventRow'
import { Avatar, Button, Confirm, DirtyGuard, EmptyState, ErrorState, Field, Loading, focusInvalid, useToast } from '../components/ui'
import { mutate, requestId } from '../lib/api'
import { fullDate, fromKst, futureLocal, statusLabel } from '../lib/format'
import { useMutation, useResource, useTitle } from '../lib/hooks'
import { useSession } from '../lib/session'
import type { EventItem, List } from '../lib/types'
export function Events() {
  useTitle('함께 달릴 모임')
  const { group } = useGroup()
  const events = useResource<List<EventItem>>(`/groups/${group.id}/events`, true)
  const [tab, setTab] = useState<'next' | 'past'>('next')
  const items = events.data?.items.filter(event => tab === 'past' ? new Date(event.starts_at).getTime() <= Date.now() : new Date(event.starts_at).getTime() > Date.now()).sort((a, b) => tab === 'next' ? a.starts_at.localeCompare(b.starts_at) : b.starts_at.localeCompare(a.starts_at))
  return <><div className="page-heading"><div><p className="eyebrow">같은 날, 같은 출발선</p><h1>함께 달릴 모임<span className="heading-dot">.</span></h1><p>기록보다 안부가 먼저인 우리의 약속.</p></div>{group.role !== 'member' && <Link className="button primary" to="new"><Plus size={18}/>모임 만들기</Link>}</div><div className="tabs" aria-label="모임 기간"><button aria-pressed={tab === 'next'} onClick={() => setTab('next')}>다가오는 모임</button><button aria-pressed={tab === 'past'} onClick={() => setTab('past')}>함께한 모임</button></div>{events.error && <ErrorState message={events.error} retry={events.refresh}/>} {events.loading ? <Loading/> : <section className="event-list"><h2 className="sr-only">모임 목록</h2>{items?.length ? items.map(event => <EventRow key={event.id} event={event}/>) : <EmptyState title={tab === 'next' ? '다음 약속을 기다리고 있어요' : '함께한 시간이 여기에 남아요'}><p>모임에서 나눈 시간이 우리 공간의 기억이 돼요.</p></EmptyState>}</section>}</>
}
export function CreateEvent() {
  useTitle('새 모임 만들기')
  const { group } = useGroup(), navigate = useNavigate(), toast = useToast()
  const [values, setValues] = useState({ title: '', description: '', location: '', starts_at: futureLocal(), ends_at: futureLocal(25), capacity: '8' })
  const [dirty, setDirty] = useState(false), [errors, setErrors] = useState<Record<string, string>>({}), [created, setCreated] = useState<number | null>(null)
  const key = useRef(requestId()), action = useMutation()
  useEffect(() => { if (created) navigate(`/groups/${group.id}/events/${created}`, { replace: true }) }, [created, navigate, group.id])
  const update = (name: keyof typeof values, value: string) => { setValues(previous => ({ ...previous, [name]: value })); setDirty(true); setErrors(previous => ({ ...previous, [name]: '' })); if (action.error) { key.current = requestId(); action.setError('') } }
  const submit = (event: FormEvent) => {
    event.preventDefault()
    const invalid: Record<string, string> = {}
    if (values.title.trim().length < 2) invalid.title = '모임 이름을 2자 이상 입력해 주세요.'
    if (values.location.trim().length < 2) invalid.location = '만날 장소를 입력해 주세요.'
    const starts = Date.parse(`${values.starts_at}:00+09:00`), ends = Date.parse(`${values.ends_at}:00+09:00`)
    if (!Number.isFinite(starts) || starts <= Date.now()) invalid.starts_at = '앞으로 시작할 시간을 선택해 주세요.'
    if (!Number.isFinite(ends) || ends <= starts || ends - starts > 86400000) invalid.ends_at = '시작 이후 24시간 안의 종료 시간을 선택해 주세요.'
    if (!/^\d+$/.test(values.capacity) || +values.capacity < 2 || +values.capacity > 100) invalid.capacity = '정원은 2~100명 사이로 입력해 주세요.'
    setErrors(invalid); if (Object.keys(invalid).length) { focusInvalid(invalid); return }
    void action.run(async () => { const result = await mutate<EventItem>(`/groups/${group.id}/events`, { ...values, starts_at: fromKst(values.starts_at), ends_at: fromKst(values.ends_at), capacity: +values.capacity, request_id: key.current }); setDirty(false); setCreated(result.id); toast('새로운 약속을 만들었어요.') })
  }
  if (group.role === 'member') return <ErrorState message="모임은 운영자가 만들 수 있어요."/>
  return <><DirtyGuard dirty={dirty} busy={action.busy}/><Link className="back-link" to={`/groups/${group.id}/events`}><ArrowLeft size={18}/>모임으로</Link><div className="page-heading"><div><p className="eyebrow">우리의 다음 약속</p><h1>모임 만들기</h1><p>정원이 차면 대기로 신청돼요. 빈자리는 먼저 기다린 멤버에게 제안해요.</p></div></div><form className="form-panel" noValidate onSubmit={submit}><fieldset disabled={action.busy}>
    <Field name="title" label="모임 이름" error={errors.title}><input id="title" maxLength={80} value={values.title} onChange={event => update('title', event.target.value)} placeholder="토요일, 강바람 한 바퀴" aria-invalid={!!errors.title} aria-describedby={errors.title ? 'title-error' : undefined}/></Field>
    <Field name="description" label="함께할 이야기" hint="거리와 페이스는 자유롭게. 참여하는 사람에게 필요한 정보를 알려주세요."><textarea id="description" className="resize-none" rows={4} maxLength={1000} value={values.description} onChange={event => update('description', event.target.value)} aria-describedby="description-help"/></Field>
    <Field name="location" label="만날 장소" error={errors.location}><input id="location" maxLength={120} value={values.location} onChange={event => update('location', event.target.value)} placeholder="망원 한강공원 시계탑 앞" aria-invalid={!!errors.location} aria-describedby={errors.location ? 'location-error' : undefined}/></Field>
    <div className="field-row">{(['starts_at', 'ends_at'] as const).map(name => <Field key={name} name={name} label={name === 'starts_at' ? '시작 · 한국 시간' : '종료 · 한국 시간'} error={errors[name]}><input id={name} type="datetime-local" value={values[name]} onChange={event => update(name, event.target.value)} aria-invalid={!!errors[name]} aria-describedby={errors[name] ? `${name}-error` : undefined}/></Field>)}</div>
    <Field name="capacity" label="함께할 정원" hint="운영자도 참가 신청을 하면 정원에 포함돼요." error={errors.capacity}><input id="capacity" type="number" inputMode="numeric" min={2} max={100} value={values.capacity} onChange={event => update('capacity', event.target.value)} aria-invalid={!!errors.capacity} aria-describedby={`capacity-help${errors.capacity ? ' capacity-error' : ''}`}/></Field>
    {action.error && <ErrorState compact message={action.error}/>}<div className="form-actions"><Button variant="secondary" disabled={action.busy} onClick={() => navigate(`/groups/${group.id}/events`)}>취소</Button><Button type="submit" busy={action.busy}>모임 만들기</Button></div></fieldset></form></>
}
export function EventDetail() {
  const { eventId = '' } = useParams(), { group } = useGroup(), { session } = useSession(), toast = useToast()
  const event = useResource<EventItem>(`/events/${eventId}`, true)
  const action = useMutation(), attendance = useMutation()
  const [confirmation, setConfirmation] = useState<'cancel-rsvp' | 'cancel-event' | null>(null)
  const pendingKey = useRef<{ action: string; id: string } | null>(null)
  useTitle(event.data?.title || '모임')
  if (event.loading) return <Loading/>
  if (!event.data || event.data.group_id !== group.id) return <ErrorState message={event.error || '이 그룹의 모임이 아니에요.'} retry={event.refresh}/>
  const item = event.data, ended = new Date(item.starts_at).getTime() <= Date.now(), active = ['confirmed', 'waitlisted', 'offered'].includes(item.my_status || '')
  const rsvp = (intent: 'join' | 'cancel' | 'accept') => void action.run(async () => {
    if (pendingKey.current?.action !== intent) pendingKey.current = { action: intent, id: requestId() }
    const result = await mutate<EventItem>(`/events/${item.id}/rsvp`, { action: intent, request_id: pendingKey.current.id })
    pendingKey.current = null; setConfirmation(null); event.refresh(); toast(intent === 'cancel' ? '신청을 취소했어요.' : result.my_status === 'waitlisted' ? '대기 신청했어요. 빈자리가 생기면 앱 알림으로 알려드려요.' : '참가가 확정됐어요.')
  })
  return <><Link className="back-link" to={`/groups/${group.id}/events`}><ArrowLeft size={18}/>모든 모임</Link><div className="event-detail-grid"><article className="event-detail"><div className="event-cover"><CalendarDays size={44}/><span>같이 달리고, 같이 쉬어요.</span></div><div className="event-detail-body"><p className="eyebrow">{ended ? '함께한 모임' : '우리의 다음 약속'} · {item.status === 'cancelled' ? '취소된 모임' : '크루 멤버 전용'}</p><h1>{item.title}</h1><div className="event-facts"><p><Clock3 size={19}/><span>{fullDate(item.starts_at)}<small>종료 {fullDate(item.ends_at)} · Asia/Seoul</small></span></p><p><MapPin size={19}/>{item.location}</p><p><Users size={19}/>{item.confirmed_count}명 참가 · 정원 {item.capacity}명{item.waiting_count > 0 ? ` · ${item.waiting_count}명 대기` : ''}</p></div><p className="event-description">{item.description || '편안한 마음으로 함께해 주세요.'}</p></div></article>
    <aside className="event-actions panel" aria-label="참가 신청 안내"><h2>{ended ? '함께한 시간' : '우리, 여기서 만나요'}</h2>{item.status === 'cancelled' ? <p className="status-banner">운영자가 취소한 모임이에요.</p> : ended ? <p className="status-banner">{item.my_attendance ? `나의 출석: ${statusLabel[item.my_attendance]}` : '이미 시작한 모임이에요.'}</p> : <><p>{item.my_status ? statusLabel[item.my_status] : '각자의 속도로, 가벼운 마음으로.'}</p>{item.my_status === 'offered' && <p className="offer-note">빈자리가 생겼어요. {item.offer_expires_at && fullDate(item.offer_expires_at)}까지 참가를 확정해 주세요.</p>}{item.my_status === 'offered' ? <Button busy={action.busy} className="full-width" onClick={() => rsvp('accept')}>참가 확정하기</Button> : !active ? <Button busy={action.busy} className="full-width" onClick={() => rsvp('join')}>{item.confirmed_count + item.offered_count >= item.capacity ? '대기 신청' : '참가 신청'}<Check size={18}/></Button> : <p className="positive-note"><Check size={18}/>{item.my_status === 'confirmed' ? '모임에서 만나요!' : '빈자리를 기다리고 있어요.'}</p>}{active && <Button variant="secondary" className="full-width" disabled={action.busy} onClick={() => { action.setError(''); setConfirmation('cancel-rsvp') }}>신청 취소</Button>}<small>대기 중 빈자리가 생기면 30분 안에 직접 확정해 주세요. 외부 푸시는 연결되지 않았어요.</small></>}{action.error && !confirmation && <ErrorState compact message={action.error}/>} {event.error && <ErrorState compact message={event.error} retry={event.refresh}/>} {group.role !== 'member' && !ended && item.status !== 'cancelled' && <Button variant="ghost" className="danger-text" onClick={() => setConfirmation('cancel-event')}>모임 전체 취소</Button>}</aside></div>
    {item.attendees && <section className="attendance-panel panel"><div className="section-heading"><div><h2>{item.can_mark_attendance ? '함께한 출석 확인' : '참가 신청 현황'}</h2><p className="muted">{item.can_mark_attendance ? '다른 운영자가 확인한 출석만 공동 기념물에 반영돼요. 수정 이력도 남아요.' : '출석은 모임 시작 이후 확인할 수 있어요.'}</p></div></div>{attendance.error && <ErrorState compact message={attendance.error}/>} {!item.attendees.length && <p className="muted">아직 참가 신청이 없어요.</p>} {item.attendees.map(person => <div className="member-row" key={person.user_id}><Avatar name={person.display_name} color={person.color}/><div><strong>{person.display_name}{person.user_id === session.user?.id ? ' · 나' : ''}</strong><small>{statusLabel[person.status]} · {statusLabel[person.attendance]}</small></div>{item.can_mark_attendance && person.status === 'confirmed' && <Button variant={person.attendance === 'present' ? 'secondary' : 'primary'} disabled={person.user_id === session.user?.id} busy={attendance.busy} title={person.user_id === session.user?.id ? '본인의 출석은 다른 운영자가 확인해야 해요.' : undefined} onClick={() => void attendance.run(async () => { await mutate(`/events/${item.id}/attendance`, { user_id: person.user_id, present: person.attendance !== 'present' }); event.refresh(); toast(person.attendance === 'present' ? '출석을 수정했어요. 공동 기록도 다시 반영돼요.' : '출석을 확인했어요. 우리 공간에 함께한 시간이 남아요.') })}>{person.attendance === 'present' ? '출석 수정' : '출석 확인'}</Button>}</div>)}<small>본인 출석은 다른 운영자가 확인해야 해요.</small></section>}
    <Confirm open={!!confirmation} title={confirmation === 'cancel-event' ? '모임 전체를 취소할까요?' : '참가 신청을 취소할까요?'} confirmLabel={confirmation === 'cancel-event' ? '모임 취소' : '신청 취소'} danger busy={action.busy} error={action.error} onClose={() => setConfirmation(null)} onConfirm={() => { if (confirmation === 'cancel-rsvp') rsvp('cancel'); else void action.run(async () => { await mutate(`/events/${item.id}/cancel`, { version: item.version }); setConfirmation(null); event.refresh(); toast('모임을 취소했어요.') }) }}><p>{confirmation === 'cancel-event' ? '모든 참가 신청이 취소돼요. 알림을 끄지 않은 참가자에게 앱 안의 알림을 남겨요.' : '확정한 자리는 다음 대기 멤버에게 제안돼요. 시작 전에는 다시 신청할 수 있어요.'}</p></Confirm>
  </>
}
