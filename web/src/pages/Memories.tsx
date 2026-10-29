import { Flag, Leaf, LockKeyhole, Sprout } from 'lucide-react'
import { useGroup } from '../components/Layout'
import { Clubhouse } from '../components/Clubhouse'
import { ErrorState, Loading } from '../components/ui'
import { useResource, useTitle } from '../lib/hooks'
import type { Growth } from '../lib/types'
export function Memories() {
  useTitle('함께한 기록')
  const { group } = useGroup(), growth = useResource<Growth>(`/groups/${group.id}/growth`, true)
  if (growth.loading) return <Loading/>
  if (!growth.data) return <ErrorState message={growth.error} retry={growth.refresh}/>
  const icons = [Flag, Leaf, Sprout]
  return <><div className="page-heading"><div><p className="eyebrow">함께한 시간의 모양</p><h1>우리의 작은 기념물<span className="heading-dot">.</span></h1><p>빨리 달려서가 아니라, 함께해서 생긴 것들.</p></div></div>{growth.error && <ErrorState compact message={growth.error} retry={growth.refresh}/>}<div className="memories-intro"><Clubhouse compact assets={growth.data.assets.filter(asset => asset.unlocked).map(asset => asset.id)} recent={growth.data.recent} palette={group.palette}/><div><Sprout size={30}/><h2>쉬는 날에도<br/>추억은 그대로예요.</h2><p>{growth.data.rule}</p><small>출석을 잘못 확인했다면 운영자가 고칠 수 있고, 그때 공동 기록도 다시 반영돼요.</small></div></div><section className="asset-list" aria-label="공동 기념물">{growth.data.assets.map((asset,index) => { const Icon = icons[index]; return <article key={asset.id} className={`asset-item ${asset.unlocked ? 'earned' : ''}`}><div className="asset-illustration"><Icon size={46}/></div><p className="eyebrow">{asset.unlocked ? '우리 공간에 함께' : '다음에 함께 만들어요'}</p><h2>{asset.name}</h2><p>{asset.description}</p><div className="asset-progress"><progress value={asset.progress} max={asset.goal} aria-label={`${asset.name} 공동 참여 기록`}/><small>{asset.progress} / {asset.goal}번의 확인된 참여</small></div></article> })}</section><p className="privacy-note"><LockKeyhole size={18}/>개인 순위나 금전 가치가 없는 공동 기념물이에요. 메시지 수, 속도, 운동량으로 보상하지 않아요.</p></>
}
