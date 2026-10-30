import { useState, useSyncExternalStore } from 'react'
import { Button, Confirm } from './ui'
import { useMutation } from '../lib/hooks'
import { BROWSER_DEMO, resetDemo, storageNotice, subscribeStorage } from '../demo/storage'
export function BrowserDemoTools() {
  const notice = useSyncExternalStore(subscribeStorage, storageNotice)
  const [confirm, setConfirm] = useState(false), action = useMutation()
  if (!BROWSER_DEMO) return null
  return <section className="browser-demo-tools" aria-label="브라우저 체험 안내"><div><strong>브라우저 체험 · 가상 인물과 시연 대화</strong><p>이 브라우저에만 저장돼요. 실제 회원 간 채팅·로그인·기기 간 동기화는 연결되지 않았어요. 개인정보는 남기지 마세요.</p>{notice && <p role="alert" className="field-error">{notice}</p>}</div><Button variant="secondary" onClick={() => setConfirm(true)}>체험 초기화</Button><Confirm open={confirm} title="이 브라우저의 체험을 초기화할까요?" confirmLabel="기록 지우고 다시 시작" danger busy={action.busy} error={action.error} onClose={() => setConfirm(false)} onConfirm={() => void action.run(async () => { await resetDemo(); window.location.replace('/auth') })}><p>이 주소에서 만든 시연 대화, 모임, 출석과 설정을 지우고 처음 샘플로 돌아가요. 다른 사이트의 데이터는 지우지 않아요.</p></Confirm></section>
}
