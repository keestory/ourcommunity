import { Link, useNavigate, useParams } from 'react-router-dom'
import { ArrowLeft, Bell, Leaf, LockKeyhole } from 'lucide-react'
import { useGroup } from '../components/Layout'
import { Clubhouse } from '../components/Clubhouse'
import { Button, EmptyState, ErrorState, Loading, useToast } from '../components/ui'
import { mutate } from '../lib/api'
import { fullDate } from '../lib/format'
import { useMutation, useResource, useTitle } from '../lib/hooks'
import { useSession } from '../lib/session'
import type { Activity, List, NotificationItem } from '../lib/types'
export function Notifications() {
  useTitle('내 알림')
  const { group } = useGroup(), notices = useResource<List<NotificationItem>>('/notifications', true), action = useMutation()
  return <><div className="page-heading"><div><p className="eyebrow">우리의 다음 이야기를 놓치지 않도록</p><h1>내 알림</h1><p>이 앱 안에서 전해 드려요. 외부 푸시는 연결되지 않았어요.</p></div><Button variant="secondary" busy={action.busy} onClick={() => void action.run(async () => { await mutate('/notifications/read'); notices.refresh() })}>모두 읽음으로 표시</Button></div>{action.error && <ErrorState compact message={action.error}/>} {notices.error && <ErrorState message={notices.error} retry={notices.refresh}/>} {notices.loading ? <Loading/> : !notices.data?.items.length ? <EmptyState title="새로운 소식이 없어요"><p>공지나 빈자리 제안이 생기면 여기서 만나요.</p></EmptyState> : <section className="notification-list">{notices.data.items.map(item => <Link className={`notification-row ${item.read ? '' : 'unread'}`} key={item.id} to={item.event_id ? `/groups/${item.group_id}/events/${item.event_id}` : `/groups/${item.group_id}/chat`}><Bell size={21}/><div><strong>{item.title}</strong><small>{fullDate(item.created_at)}{!item.read ? ' · 읽지 않음' : ''}</small></div></Link>)}</section>}<Link className="back-link" to={`/groups/${group.id}/space`}><ArrowLeft size={17}/>우리 공간으로</Link></>
}
export function Invite() {
  useTitle('크루의 초대')
  const { token = '' } = useParams(), { session, loading } = useSession(), navigate = useNavigate(), toast = useToast()
  const invite = useResource<{ name: string; description: string; group_id: string; history_policy: string }>(`/invites/${token}`), action = useMutation()
  if (loading || invite.loading) return <Loading/>
  return <main className="invite-page"><Link to="/" className="wordmark"><Leaf size={25}/>ourcommunity.</Link>{invite.data ? <><Clubhouse compact/><p className="eyebrow">함께할 자리를 마련했어요</p><h1>{invite.data.name}</h1><p>{invite.data.description}</p><p className="privacy-note"><LockKeyhole size={18}/>{invite.data.history_policy}</p><p className="muted">집계 참여는 기본으로 꺼져 있어요. 가입 후 설정에서 직접 선택할 수 있어요.</p>{session.user ? <Button busy={action.busy} onClick={() => void action.run(async () => { const group = await mutate<{ id: string }>(`/invites/${token}/join`); toast('크루에 함께하게 됐어요. 반가워요!'); navigate(`/groups/${group.id}/space`, { replace: true }) })}>이 크루에 함께하기</Button> : <Link className="button primary" to={`/auth?next=${encodeURIComponent(`/invite/${token}`)}`}>로그인하고 초대 확인하기</Link>}</> : <ErrorState message={invite.error} retry={invite.refresh}/>} {action.error && <ErrorState compact message={action.error}/>}</main>
}
export function PublicSpace() {
  useTitle('공개된 공동 공간')
  const { groupId = '' } = useParams()
  const group = useResource<{ id: string; name: string; description: string; palette: string; assets: { id: string; name: string; description: string }[]; recent: Activity }>(`/public/groups/${groupId}`, true)
  return <main className="public-page"><Link className="wordmark" to="/"><Leaf size={25}/>ourcommunity.</Link>{group.loading ? <Loading/> : group.data ? <>{group.error && <ErrorState compact message={`최신 공개 상태를 확인하지 못했어요. ${group.error}`} retry={group.refresh}/>}<div className="page-heading"><div><p className="eyebrow">함께한 시간이 만든 공간 · 로컬 시제품</p><h1>{group.data.name}</h1><p>{group.data.description}</p></div></div><Clubhouse assets={group.data.assets.map(asset => asset.id)} recent={group.data.recent} palette={group.data.palette}/><p className="privacy-note"><LockKeyhole size={18}/>대화는 멤버들끼리만. 여기는 공동 공간과 보호된 분위기만 보여요.</p><div className="public-assets">{group.data.assets.map(asset => <article key={asset.id}><h2>{asset.name}</h2><p>{asset.description}</p></article>)}</div></> : <ErrorState message={group.error} retry={group.refresh}/>}<Link className="back-link" to="/"><ArrowLeft size={17}/>내 공간으로</Link></main>
}
