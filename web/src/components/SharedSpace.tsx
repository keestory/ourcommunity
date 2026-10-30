import { useState } from 'react'
import { Armchair, Flag, LockKeyhole, MoveRight, Trees } from 'lucide-react'
import { Button, ErrorState, useToast } from './ui'
import { mutate } from '../lib/api'
import { useMutation } from '../lib/hooks'
import { BROWSER_DEMO } from '../demo/storage'
import type { Group, Growth, SpaceSlot } from '../lib/types'
const slots: { id: SpaceSlot; name: string }[] = [{ id: 'entry', name: '입구' }, { id: 'center', name: '쉼터' }, { id: 'garden', name: '정원' }]
const defaults: Record<string, SpaceSlot> = { 'trail-sign': 'entry', bench: 'center', 'memory-tree': 'garden' }
export function AssetIcon({ id, size = 28 }: { id: string; size?: number }) { const Icon = id === 'trail-sign' ? Flag : id === 'bench' ? Armchair : Trees; return <Icon size={size} strokeWidth={1.7} aria-hidden="true"/> }
export function SharedSpace({ group, growth, editable = false, refresh }: { group: Group; growth: Growth; editable?: boolean; refresh?: () => void }) {
  const [selected, setSelected] = useState('bench'), action = useMutation(), toast = useToast()
  const layout = { ...defaults, ...group.space_layout }, asset = growth.assets.find(a => a.id === selected)
  const canArrange = editable && BROWSER_DEMO && group.role === 'owner'
  const move = (slot: SpaceSlot) => void action.run(async () => { await mutate(`/groups/${group.id}/space`, { asset_id: selected, slot, version: group.version }, 'PATCH'); refresh?.(); toast('기념물 위치를 저장했어요. 우리 공간에 반영됐어요.') })
  return <div className={`shared-space ${editable ? 'space-editor' : 'space-preview'} ${group.palette}`}><div className="space-map" aria-label="공동 기념물이 놓인 크루 공간">
    <svg viewBox="0 0 640 260" aria-hidden="true" focusable="false"><path d="M-20 226C130 226 85 45 260 45S440 226 660 226" className="map-trail"/><path d="M-20 226C130 226 85 45 260 45S440 226 660 226" className="map-trail-line"/><circle cx="542" cy="55" r="37" className="map-garden"/><circle cx="580" cy="79" r="26" className="map-garden"/><path d="M28 36h44m-22-22v44" className="map-mark"/></svg>
    <span className="map-caption">OUR SHARED PLACE</span>
    {growth.assets.map(a => <button key={a.id} className={`space-object slot-${layout[a.id]} ${a.unlocked ? 'unlocked' : 'locked'} ${editable && selected === a.id ? 'selected' : ''}`} onClick={() => { setSelected(a.id); action.setError('') }} aria-pressed={editable ? selected === a.id : undefined} aria-label={`${a.name.replace('우리의 첫 ', '').replace('잠깐 쉬어 가는 ', '').replace('함께 자라는 ', '')} ${slots.find(slot => slot.id === layout[a.id])?.name} · ${a.name} ${a.unlocked ? '살펴보기' : '만드는 방법 보기'}`} disabled={!editable}><span className="space-object-symbol">{a.unlocked ? <AssetIcon id={a.id} size={34}/> : <LockKeyhole size={24}/>}</span><strong>{a.name.replace('우리의 첫 ', '').replace('잠깐 쉬어 가는 ', '').replace('함께 자라는 ', '')}</strong>{' '}<small>{slots.find(slot => slot.id === layout[a.id])?.name}</small></button>)}
  </div>{editable && asset && <div className="space-selection"><div className="space-selection-heading"><AssetIcon id={asset.id}/><div><strong>{asset.name}</strong><p>{asset.unlocked ? '함께 만든 기념물이에요. 쉬어도 사라지지 않아요.' : `확인된 참여 ${Math.max(0, asset.goal - asset.progress)}번이 더 쌓이면 우리 공간에 놓여요.`}</p></div></div>{canArrange && asset.unlocked ? <div className="space-placement" aria-label="기념물 배치 위치"><span>위치 바꾸기 <MoveRight size={15}/></span>{slots.map(slot => <Button key={slot.id} variant={layout[asset.id] === slot.id ? 'primary' : 'secondary'} aria-pressed={layout[asset.id] === slot.id} disabled={layout[asset.id] === slot.id} busy={action.busy} onClick={() => move(slot.id)}>{slot.name}</Button>)}</div> : <p className="space-hint">{!asset.unlocked ? '모임 참여 → 운영자 출석 확인 → 공동 기념물' : editable && BROWSER_DEMO ? '운영자 역할에서는 기념물의 위치도 바꿀 수 있어요.' : '이 공간은 확인된 공동 참여를 보여줘요.'}</p>}{action.error && <ErrorState compact message={action.error}/>}</div>}</div>
}
