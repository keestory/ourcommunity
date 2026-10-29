import { useState, type FormEvent } from 'react'
import { Eye, EyeOff, Leaf, ArrowRight } from 'lucide-react'
import { Navigate, useSearchParams } from 'react-router-dom'
import { useSession } from '../lib/session'
import { useMutation, useTitle } from '../lib/hooks'
import { safeNext } from '../lib/format'
import { Button, ErrorState, Field, Loading, focusInvalid } from '../components/ui'
import { Clubhouse } from '../components/Clubhouse'
export function Auth() {
  useTitle('함께할 공간에 들어가기')
  const { session, loading, error, refresh, login } = useSession()
  const [search] = useSearchParams()
  const [register, setRegister] = useState(false)
  const [show, setShow] = useState(false)
  const [fields, setFields] = useState<Record<string, string>>({})
  const action = useMutation()
  if (loading) return <Loading/>
  if (session.user) return <Navigate to={safeNext(search.get('next'))} replace/>
  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const data = new FormData(event.currentTarget)
    const username = String(data.get('username') || '').trim(), password = String(data.get('password') || ''), display_name = String(data.get('display_name') || '').trim()
    const errors: Record<string, string> = {}
    if (!/^[a-zA-Z0-9_-]{3,40}$/.test(username)) errors.username = '영문, 숫자, _ 또는 -로 3~40자를 입력해 주세요.'
    if (!password || (register && password.length < 10)) errors.password = register ? '비밀번호를 10자 이상 입력해 주세요.' : '비밀번호를 입력해 주세요.'
    if (register && !display_name) errors.display_name = '함께 부를 이름을 입력해 주세요.'
    setFields(errors); if (Object.keys(errors).length) { focusInvalid(errors); return }
    void action.run(() => login(register ? 'register' : 'login', register ? { username, password, display_name } : { username, password }))
  }
  return <main className="auth-page"><section className="auth-story"><span className="wordmark"><Leaf size={28}/>ourcommunity.</span><div><p className="eyebrow">함께한 시간이, 우리의 공간이 되는 곳</p><h1>대화는 우리끼리.<br/>좋은 시간은 함께 자라요.</h1><p>달리기 전의 설렘부터 끝나고 나누는 이야기까지.<br/>함께 머물고 싶은 크루의 작은 집.</p></div><Clubhouse assets={['trail-sign', 'bench', 'memory-tree']}/><small>그림은 공간 표현 예시예요. 실제 기념물은 확인된 참여로 생겨요.</small></section>
    <section className="auth-form"><div className="auth-form-inner"><p className="eyebrow">WELCOME TO OUR PLACE</p><h2>{register ? '함께 부를 이름을 알려주세요' : '우리 공간에 들어가기'}</h2><p className="muted">로컬에서 실행하는 첫 제품입니다. 실제 개인정보 대신 테스트 정보를 사용해 주세요.</p>
      {error && <ErrorState message={error} retry={() => void refresh()}/>}<form noValidate onSubmit={submit}>
      {register && <Field label="이름" name="display_name" error={fields.display_name}><input id="display_name" name="display_name" maxLength={30} autoComplete="nickname" aria-invalid={!!fields.display_name} aria-describedby={fields.display_name ? 'display_name-error' : undefined}/></Field>}
      <Field label="아이디" name="username" error={fields.username}><input id="username" name="username" autoComplete="username" maxLength={40} aria-invalid={!!fields.username} aria-describedby={fields.username ? 'username-error' : undefined}/></Field>
      <Field label="비밀번호" name="password" error={fields.password}><div className="password-field"><input id="password" name="password" type={show ? 'text' : 'password'} autoComplete={register ? 'new-password' : 'current-password'} maxLength={128} aria-invalid={!!fields.password} aria-describedby={fields.password ? 'password-error' : undefined}/><button type="button" aria-label={show ? '비밀번호 숨기기' : '비밀번호 보기'} onClick={() => setShow(!show)}>{show ? <EyeOff size={19}/> : <Eye size={19}/>}</button></div></Field>
      {action.error && <ErrorState compact message={action.error}/>}<Button type="submit" busy={action.busy} className="full-width">{register ? '로컬 계정 만들기' : '로그인'}<ArrowRight size={18}/></Button></form>
      <Button variant="ghost" className="full-width" onClick={() => { setRegister(!register); setFields({}); action.setError('') }}>{register ? '이미 계정이 있어요 · 로그인' : '처음이에요 · 로컬 계정 만들기'}</Button>
      {session.demo && <div className="demo-login"><span>샘플 크루 체험하기</span><div><Button variant="secondary" busy={action.busy} onClick={() => void action.run(() => login('demo', { persona: 'sora' }))}>멤버로 둘러보기</Button><Button variant="secondary" busy={action.busy} onClick={() => void action.run(() => login('demo', { persona: 'mira' }))}>운영자로 둘러보기</Button></div><small>가상의 인물과 데이터예요. 외부 계정·푸시는 연결되지 않았어요.</small></div>}
    </div></section></main>
}
