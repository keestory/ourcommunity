import { Check, LockKeyhole, ArrowUpRight } from 'lucide-react'
import { Link } from 'react-router-dom'
import { BROWSER_DEMO } from '../demo/storage'
import { useGroup } from '../components/Layout'
import { SharedSpace, AssetIcon } from '../components/SharedSpace'
import { ErrorState, Loading } from '../components/ui'
import { useResource, useTitle } from '../lib/hooks'
import type { EventItem, Growth, List } from '../lib/types'
export function Memories() {
  useTitle('함께한 기록')
  const { group, refreshGroup } = useGroup(), growth = useResource<Growth>(`/groups/${group.id}/growth`, true), events = useResource<List<EventItem>>(`/groups/${group.id}/events`)
  if (growth.loading) return <Loading/>
  if (!growth.data) return <ErrorState message={growth.error} retry={growth.refresh}/>
  const past = events.data?.items.find(e => e.can_mark_attendance && e.status === 'published')
  return <><div className="page-heading"><div><p className="eyebrow">함께한 기록</p><h1>함께 만든 공간</h1><p>{BROWSER_DEMO ? '기념물을 눌러 살펴보세요. 운영자는 만든 기념물의 위치를 바꿀 수 있어요.' : '함께 만든 기념물을 살펴보고, 다음 모임에서 기록을 이어가세요.'}</p></div>{past && <Link className="button secondary" to={`/groups/${group.id}/events/${past.id}`}>출석 확인 <ArrowUpRight size={17}/></Link>}</div>{growth.error && <ErrorState compact message={growth.error} retry={growth.refresh}/>}<div className="growth-workspace"><SharedSpace group={group} growth={growth.data} editable refresh={refreshGroup}/><section className="asset-list" aria-label="공동 기념물">{growth.data.assets.map(asset => <article key={asset.id} className={`asset-item ${asset.unlocked ? 'earned' : ''}`}><div className="asset-illustration"><AssetIcon id={asset.id} size={28}/></div><div className="asset-description"><p className="eyebrow">{asset.unlocked ? <><Check size={13}/>우리 공간에 함께</> : '다음에 함께 만들어요'}</p><h2>{asset.name}</h2><p>{asset.description}</p><div className="asset-progress"><progress value={asset.progress} max={asset.goal} aria-label={`${asset.name} 공동 참여 기록`}/><small>{asset.progress} / {asset.goal}번의 확인된 참여</small></div></div></article>)}</section></div><div className="growth-notes"><p><LockKeyhole size={16}/>메시지 수나 개인 순위로 보상하지 않아요. 쉬어도 기념물은 남고, 잘못 확인한 출석은 정정할 수 있어요.</p><p>최근 활기: {growth.data.recent.visible ? growth.data.recent.label : '집계를 공개하지 않아요.'} 대화 원문이나 개인 접속 상태는 이 공간에 표시하지 않아요.</p></div></>
}
