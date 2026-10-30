import { Bell, CalendarDays, ChevronRight, House, Leaf, LogOut, MessageCircle, Settings, Sprout } from 'lucide-react'
import { Link, Navigate, NavLink, Outlet, useLocation, useOutletContext, useParams } from 'react-router-dom'
import { useState } from 'react'
import { useSession } from '../lib/session'
import { useMutation, useResource } from '../lib/hooks'
import type { Group, List, NotificationItem } from '../lib/types'
import { Avatar, Button, Confirm, EmptyState, ErrorState, Loading } from './ui'
export function Protected() {
  const { session, loading, error, refresh } = useSession()
  const location = useLocation()
  if (loading) return <Loading/>
  if (error) return <main className="auth-error"><ErrorState message={error} retry={() => void refresh()}/></main>
  if (!session.user) return <Navigate to={`/auth?next=${encodeURIComponent(location.pathname + location.search)}`} replace/>
  return <Outlet key={session.user.id}/>
}
export function GroupIndex() {
  const groups = useResource<List<Group>>('/groups')
  const { logout } = useSession()
  const action = useMutation()
  if (groups.loading) return <Loading/>
  if (groups.error) return <ErrorState message={groups.error} retry={groups.refresh}/>
  if (groups.data?.items[0]) return <Navigate to={`/groups/${groups.data.items[0].id}/space`} replace/>
  return <main className="narrow-page"><Link to="/" className="wordmark"><Leaf size={24}/>ourcommunity</Link><EmptyState title="함께할 공간을 기다리고 있어요"><p>운영자에게 받은 초대 링크를 열면 크루에 함께할 수 있어요.</p></EmptyState>{action.error && <ErrorState message={action.error}/>}<Button variant="secondary" busy={action.busy} onClick={() => void action.run(logout)}>로그아웃</Button></main>
}
export type GroupContext = { group: Group; refreshGroup: () => void }
export const useGroup = () => useOutletContext<GroupContext>()
export function Layout() {
  const { groupId = '' } = useParams()
  const { session, logout } = useSession()
  const resource = useResource<Group>(`/groups/${groupId}`, true)
  const notices = useResource<List<NotificationItem>>('/notifications', true)
  const [confirmLogout, setConfirmLogout] = useState(false)
  const action = useMutation()
  const nav = [{ path: 'space', label: '우리 공간', icon: House }, { path: 'chat', label: '대화', icon: MessageCircle }, { path: 'events', label: '모임', icon: CalendarDays }, { path: 'memories', label: '함께한 기록', icon: Sprout }, { path: 'settings', label: '설정', icon: Settings }]
  if (resource.loading) return <Loading/>
  if (!resource.data) return <main className="narrow-page"><ErrorState message={resource.error || '이 공간에 접근할 수 없어요.'} retry={resource.refresh}/><Link className="text-link" to="/">내 공간으로 돌아가기 <ChevronRight size={16}/></Link></main>
  const group = resource.data
  const unread = notices.data?.items.some(item => !item.read)
  return <div className="app-shell"><aside className="sidebar" aria-label="커뮤니티 탐색"><Link to={`/groups/${group.id}/space`} className="wordmark"><Leaf size={25} aria-hidden="true"/>ourcommunity<span className="wordmark-dot">.</span></Link><div className="sidebar-group"><span className="group-symbol"><Sprout size={25}/></span><div><strong>{group.name}</strong><small>함께 만들어 가는 곳</small></div></div><nav aria-label="주 메뉴">{nav.map(item => <NavLink key={item.path} to={`/groups/${group.id}/${item.path}`}><item.icon size={21} aria-hidden="true"/><span>{item.label}</span></NavLink>)}</nav><div className="sidebar-bottom"><div className="quiet-note"><Leaf size={19}/><p>빠른 기록보다<br/>함께 쌓이는 시간.</p></div><button className="account-row" onClick={() => setConfirmLogout(true)}><Avatar name={session.user!.display_name} color={session.user!.color}/><span><strong>{session.user!.display_name}</strong><small>{group.role === 'owner' ? '크루 운영자' : group.role === 'organizer' ? '모임 운영자' : '크루 멤버'}</small></span><LogOut size={18}/></button></div></aside>
    <div className="main-area"><header className="topbar"><span className="breadcrumb">나의 커뮤니티 <ChevronRight size={14}/><strong>{group.name}</strong></span><span className="mobile-brand"><Leaf size={19}/>ourcommunity</span><div className="topbar-actions">{session.demo && <span className="demo-label">{session.preview?.enabled ? '체험 전용 · 가상 데이터' : '로컬 체험 · 샘플 데이터'}</span>}<Link className="icon-button notification-button" to={`/groups/${group.id}/notifications`} aria-label={unread ? '알림 · 읽지 않은 알림 있음' : '알림'}><Bell size={21}/>{unread && <span className="notification-dot"/>}</Link><button className="mobile-account icon-button" aria-label="계정과 로그아웃" onClick={() => setConfirmLogout(true)}><Avatar small name={session.user!.display_name}/></button></div></header>
      <main id="main" className="content">{session.preview?.enabled && <p className="privacy-note preview-note">이 브라우저만의 체험 공간 · 첫 방문 1시간 뒤{session.preview.restart_resets !== false ? ' 또는 서버 재시작 시' : ''} 초기화돼요. 실제 개인정보는 남기지 마세요.</p>}{resource.error && <ErrorState compact message={`최신 상태를 확인하지 못했어요. ${resource.error}`} retry={resource.refresh}/>}<Outlet context={{ group, refreshGroup: resource.refresh } satisfies GroupContext}/></main>
    </div><Confirm open={confirmLogout} title={session.preview?.enabled ? '다른 역할로 둘러볼까요?' : '로그아웃할까요?'} confirmLabel={session.preview?.enabled ? '역할 다시 선택' : '로그아웃'} busy={action.busy} error={action.error} onClose={() => setConfirmLogout(false)} onConfirm={() => void action.run(async () => { await logout(); setConfirmLogout(false) })}><p>{session.preview?.enabled ? '가상 역할을 다시 선택해도 체험 시간이 끝나기 전까지 이 브라우저의 기록은 이어져요. 보내지 않은 글은 사라져요.' : '저장된 대화와 기록은 다음 로그인에도 이어져요. 아직 보내지 않은 글은 사라져요.'}</p></Confirm></div>
}
