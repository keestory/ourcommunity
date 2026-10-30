import { useEffect, useRef, useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { CalendarDays, LockKeyhole, Megaphone, MoreHorizontal, Plus, Send } from 'lucide-react'
import { BROWSER_DEMO } from '../demo/storage'
import { useGroup } from '../components/Layout'
import { Avatar, Button, Confirm, Dialog, DirtyGuard, EmptyState, ErrorState, Field, Loading, useToast } from '../components/ui'
import { api, mutate, requestId } from '../lib/api'
import { clock, fullDate } from '../lib/format'
import { useMutation, useResource, useTitle } from '../lib/hooks'
import type { Announcement, List, Message, MessagePage } from '../lib/types'
export function Chat() {
  useTitle('우리끼리 대화')
  const { group } = useGroup(), toast = useToast()
  const [before, setBefore] = useState<number | null>(null)
  const messages = useResource<MessagePage>(`/groups/${group.id}/messages?limit=50${before ? `&before=${before}` : ''}`, true)
  const news = useResource<List<Announcement>>(`/groups/${group.id}/announcements`, true)
  const [draft, setDraft] = useState(''), [draftError, setDraftError] = useState('')
  const [selection, setSelection] = useState<Message | null>(null)
  const [operation, setOperation] = useState<'delete' | 'block' | 'report' | null>(null)
  const [reason, setReason] = useState('')
  const [announcement, setAnnouncement] = useState(false), [announcementBody, setAnnouncementBody] = useState(''), [discard, setDiscard] = useState(false)
  const messageKey = useRef(requestId()), announcementKey = useRef(requestId())
  const log = useRef<HTMLDivElement>(null), nearBottom = useRef(true), readCursor = useRef(0)
  const send = useMutation(), safety = useMutation(), publish = useMutation()
  const staff = group.role !== 'member'
  useEffect(() => {
    if (nearBottom.current && log.current) log.current.scrollTop = log.current.scrollHeight
    const current = messages.data?.items.at(-1)?.seq
    if (current && current > readCursor.current && nearBottom.current && document.visibilityState === 'visible' && !before) {
      readCursor.current = current
      void mutate(`/groups/${group.id}/read`, { seq: current }).catch(() => { readCursor.current = 0 })
    }
  }, [messages.data, group.id, before])
  const submit = (event?: FormEvent) => {
    event?.preventDefault()
    if (!draft.trim()) { setDraftError('나누고 싶은 이야기를 입력해 주세요.'); document.getElementById('message')?.focus(); return }
    setDraftError('')
    const body = draft.trim()
    void send.run(async () => { await mutate(`/groups/${group.id}/messages`, { client_id: messageKey.current, body }); messageKey.current = requestId(); setDraft(''); nearBottom.current = true; setBefore(null); messages.refresh() })
  }
  const safetyAction = () => void safety.run(async () => {
    if (!selection) return
    if (operation === 'delete') await mutate(`/messages/${selection.id}`, undefined, 'DELETE')
    if (operation === 'block') await mutate(`/groups/${group.id}/blocks/${selection.author.id}`)
    if (operation === 'report') { if (reason.trim().length < 2) { safety.setError('신고 이유를 2자 이상 알려 주세요.'); document.getElementById('reason')?.focus(); return }; await mutate(`/groups/${group.id}/reports`, { message_id: selection.id, reason }) }
    toast(operation === 'report' ? BROWSER_DEMO ? '이 브라우저의 시연 신고함에 기록했어요. 실제 운영자에게 전달되지 않아요.' : '신고를 운영자에게 전달했어요.' : operation === 'block' ? '서로의 대화 메시지를 숨겼어요.' : '메시지를 삭제했어요.'); setSelection(null); setOperation(null); setReason(''); messages.refresh()
  })
  const dirty = !!draft.trim() || !!announcementBody.trim() || !!reason.trim()
  if (messages.loading) return <><DirtyGuard dirty={dirty} busy={send.busy || publish.busy}/><Loading label="대화를 불러오고 있어요"/></>
  if (!messages.data) return <><DirtyGuard dirty={dirty} busy={send.busy || publish.busy}/><ErrorState message={messages.error} retry={messages.refresh}/></>
  return <><DirtyGuard dirty={dirty} busy={send.busy || publish.busy}/><div className="page-heading"><div><p className="eyebrow">멤버만 볼 수 있는 대화</p><h1>오늘의 이야기를 나눠요<span className="heading-dot">.</span></h1><p>다음 달리기 약속도, 다녀온 뒤의 작은 안부도.</p></div><Link className="button secondary" to={`/groups/${group.id}/events`}><CalendarDays size={18}/>모임 보기</Link></div>
    <div className="chat-layout"><section className="chat-panel" aria-label="그룹 대화"><div className="chat-heading"><span><LockKeyhole size={16}/>{group.name}</span><small>멤버 전용</small></div>{messages.error && <ErrorState compact message={`최신 대화와 연결되지 않았어요. ${messages.error}`} retry={messages.refresh}/>}
      <div className="chat-log" ref={log} role="log" aria-label="대화 내용" aria-live="off" tabIndex={0} onScroll={() => { const element = log.current; if (element) nearBottom.current = element.scrollHeight - element.scrollTop - element.clientHeight < 70 }}>
      <div className="chat-pagination">{messages.data.has_more && <Button variant="ghost" onClick={() => { setBefore(messages.data!.items[0].seq); nearBottom.current = false }}>이전 대화 50개 보기</Button>}{before && <Button variant="secondary" onClick={() => { setBefore(null); nearBottom.current = true }}>최신 대화로 돌아가기</Button>}</div>
      {!messages.data.items.length && <EmptyState title="첫 이야기를 기다리고 있어요"><p>반가운 인사를 남겨 보세요. 가입 이전의 대화는 보이지 않아요.</p></EmptyState>}
      {messages.data.items.map(message => <article className={`message ${message.mine ? 'mine' : ''}`} key={message.id}><Avatar name={message.author.display_name} color={message.author.color}/><div className="message-content"><div className="message-meta"><strong>{message.author.display_name}{message.mine ? ' · 나' : ''}</strong><time dateTime={message.created_at} title={fullDate(message.created_at)}>{clock(message.created_at)}</time></div><p className={message.deleted ? 'deleted-message' : ''}>{message.deleted ? '삭제된 메시지예요.' : message.body}</p></div>{!message.deleted && <Button variant="ghost" className="icon-button message-menu" aria-label={`${message.author.display_name} 메시지 메뉴`} onClick={() => { setSelection(message); setOperation(null); safety.setError('') }}><MoreHorizontal size={18}/></Button>}</article>)}
      </div><form className="chat-composer" noValidate onSubmit={submit}><label htmlFor="message" className="sr-only">메시지</label><textarea id="message" value={draft} maxLength={2000} rows={2} className="resize-none" placeholder="함께 나누고 싶은 이야기…" aria-invalid={!!draftError} aria-describedby={draftError ? 'message-error' : 'message-help'} disabled={send.busy} onChange={event => { setDraft(event.target.value); setDraftError(''); if (send.error) { messageKey.current = requestId(); send.setError('') } }} onKeyDown={event => { if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing && event.keyCode !== 229) { event.preventDefault(); submit() } }}/><Button type="submit" busy={send.busy} aria-label="메시지 보내기"><Send size={19}/><span>보내기</span></Button><small id="message-help">Enter로 보내기 · Shift + Enter로 줄바꿈</small>{draftError && <p className="field-error" id="message-error">{draftError}</p>}{send.error && <ErrorState compact message={send.error}/>}</form></section>
    <aside className="chat-side" aria-label="공지와 대화 안내"><section className="panel"><div className="section-heading"><h2><Megaphone size={19}/>우리의 공지</h2>{staff && <Button variant="ghost" className="icon-button" aria-label="공지 올리기" onClick={() => setAnnouncement(true)}><Plus size={20}/></Button>}</div>{news.error && <ErrorState compact message={news.error} retry={news.refresh}/>} {!news.data?.items.length && <p className="muted">아직 공지가 없어요.</p>}{news.data?.items.map(item => <article className="announcement" key={item.id}><p>{item.body}</p><small>{item.author_name} · {fullDate(item.created_at)}</small></article>)}</section><p className="privacy-note"><LockKeyhole size={17}/>대화 원문은 밖으로 공개되지 않아요. 메시지 수로 기념물이나 개인 순위를 만들지 않아요.</p></aside></div>
    <Dialog open={!!selection && !operation} title="이 메시지 관리하기" onClose={() => setSelection(null)}><div className="menu-actions">{(selection?.mine || staff) && <Button variant="secondary" onClick={() => setOperation('delete')}>메시지 삭제</Button>}{!selection?.mine && <><Button variant="secondary" onClick={() => setOperation('report')}>메시지 신고</Button><Button variant="secondary" onClick={() => setOperation('block')}>이 멤버의 대화 차단</Button></>}</div></Dialog>
    <Confirm open={!!operation} title={operation === 'delete' ? '메시지를 삭제할까요?' : operation === 'block' ? '서로의 대화를 숨길까요?' : '운영자에게 신고하기'} confirmLabel={operation === 'report' ? '신고 보내기' : operation === 'block' ? '대화 차단' : '삭제'} danger={operation === 'delete'} busy={safety.busy} error={safety.error} onConfirm={safetyAction} onClose={() => { setOperation(null); setSelection(null); setReason('') }}>{operation === 'report' ? <Field name="reason" label="신고 이유"><textarea id="reason" className="resize-none" rows={3} maxLength={300} value={reason} onChange={event => setReason(event.target.value)}/></Field> : <p>{operation === 'block' ? '서로의 대화 메시지만 숨겨요. 공지와 멤버 목록, 모임 출석 기록은 그대로 보일 수 있어요. 설정에서 해제할 수 있어요.' : '본문은 지워지고 삭제 표시가 남아요. 이 작업은 되돌릴 수 없어요.'}</p>}</Confirm>
    <Dialog open={announcement} title="크루에 공지 올리기" onClose={() => announcementBody ? setDiscard(true) : setAnnouncement(false)} busy={publish.busy}><form noValidate onSubmit={event => { event.preventDefault(); if (!announcementBody.trim()) { publish.setError('공지 내용을 입력해 주세요.'); document.getElementById('announcement')?.focus(); return }; void publish.run(async () => { await api(`/groups/${group.id}/announcements`, { method: 'POST', body: JSON.stringify({ body: announcementBody, request_id: announcementKey.current }) }); setAnnouncementBody(''); setAnnouncement(false); announcementKey.current = requestId(); news.refresh(); toast('공지를 올렸어요.') }) }}><Field label="공지 내용" name="announcement"><textarea id="announcement" className="resize-none" rows={5} maxLength={2000} value={announcementBody} onChange={event => { setAnnouncementBody(event.target.value); if (publish.error) { announcementKey.current = requestId(); publish.setError('') } }}/></Field>{publish.error && <ErrorState compact message={publish.error}/>}<div className="dialog-actions"><Button variant="secondary" disabled={publish.busy} onClick={() => announcementBody ? setDiscard(true) : setAnnouncement(false)}>취소</Button><Button type="submit" busy={publish.busy}>공지 올리기</Button></div></form></Dialog>
    <Confirm open={discard} title="작성한 공지를 버릴까요?" confirmLabel="내용 버리기" onClose={() => setDiscard(false)} onConfirm={() => { setDiscard(false); setAnnouncementBody(''); setAnnouncement(false); announcementKey.current = requestId() }}><p>아직 올리지 않은 공지는 저장되지 않아요.</p></Confirm>
  </>
}
