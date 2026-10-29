import { ArrowRight, LockKeyhole, Megaphone, Sprout } from 'lucide-react'
import { Link } from 'react-router-dom'
import { useGroup } from '../components/Layout'
import { Clubhouse } from '../components/Clubhouse'
import { EventRow } from '../components/EventRow'
import { ErrorState, Loading } from '../components/ui'
import { useResource, useTitle } from '../lib/hooks'
import type { Announcement, EventItem, Growth, List } from '../lib/types'
export function Space() {
  const { group } = useGroup()
  useTitle('우리 공간')
  const growth = useResource<Growth>(`/groups/${group.id}/growth`, true)
  const events = useResource<List<EventItem>>(`/groups/${group.id}/events`, true)
  const news = useResource<List<Announcement>>(`/groups/${group.id}/announcements`, true)
  if (growth.loading) return <Loading/>
  if (!growth.data) return <ErrorState message={growth.error} retry={growth.refresh}/>
  const unlocked = growth.data.assets.filter(asset => asset.unlocked)
  const upcoming = events.data?.items.filter(event => new Date(event.starts_at).getTime() > Date.now() && event.status !== 'cancelled').sort((a,b) => a.starts_at.localeCompare(b.starts_at))[0]
  return <><div className="page-heading"><div><p className="eyebrow">{group.subtitle}</p><h1>{group.name}<span className="heading-dot">.</span></h1><p>{group.description}</p></div><span className="privacy-label"><LockKeyhole size={14}/>{group.public_space ? '공간만 공개' : '우리끼리의 공간'}</span></div>
  {growth.error && <ErrorState compact message={growth.error} retry={growth.refresh}/>}<div className="space-grid"><section className="space-main"><Clubhouse assets={unlocked.map(asset => asset.id)} recent={growth.data.recent} palette={group.palette}/><div className="scene-footnote"><span><LockKeyhole size={14}/>대화 내용과 개인의 활동은 이 풍경에 공개되지 않아요.</span><Link to={`/groups/${group.id}/settings`}>공개 범위</Link></div>
    <section className="memory-preview"><div><p className="eyebrow">함께 쌓이는 작은 변화</p><h2>우리의 시간으로 만든 공간</h2><p>이정표도, 쉬어 갈 벤치도.<br className="desktop-break"/> 함께한 날들이 하나씩 남아요.</p><Link className="text-link" to={`/groups/${group.id}/memories`}>함께한 기록 보기 <ArrowRight size={16}/></Link></div><div className="memory-miniatures">{growth.data.assets.map((asset, index) => <div key={asset.id} className={asset.unlocked ? 'unlocked' : 'locked'}><span className={`mini-asset asset-${index}`} aria-hidden="true">{index === 0 ? '↗' : index === 1 ? '⌑' : '♧'}</span><strong>{asset.name.replace('우리의 첫 ', '').replace('잠깐 쉬어 가는 ', '').replace('함께 자라는 ', '')}</strong><small>{asset.unlocked ? '우리 공간에 있어요' : '다음에 함께 만들어요'}</small></div>)}</div></section>
  </section><aside className="space-side" aria-label="다음 모임과 공지"><section className="next-meeting"><div className="section-heading"><h2>다음에 만나요</h2><Link to={`/groups/${group.id}/events`} aria-label="모든 모임 보기"><ArrowRight size={20}/></Link></div>{events.error && <ErrorState compact message={events.error} retry={events.refresh}/>} {events.loading ? <Loading label="모임을 불러오는 중"/> : upcoming ? <EventRow event={upcoming}/> : <p className="muted">다음 모임이 생기면 여기에 보여요.</p>}<Link className="button secondary full-width" to={upcoming ? `/groups/${group.id}/events/${upcoming.id}` : `/groups/${group.id}/events`}>모임 살펴보기 <ArrowRight size={16}/></Link></section>
    <section className="announcement-preview"><span className="section-icon"><Megaphone size={20}/></span><h2>우리 크루의 이야기</h2>{news.error && <ErrorState compact message={news.error} retry={news.refresh}/>}<p>{news.data?.items[0]?.body || '아직 새 공지가 없어요.'}</p><Link className="text-link" to={`/groups/${group.id}/chat`}>대화에 함께하기 <ArrowRight size={16}/></Link></section><div className="gentle-note"><Sprout size={23}/><p>잠시 쉬어도 괜찮아요.<br/>함께 만든 기억은 여기 남아 있어요.</p></div></aside></div></>
}
