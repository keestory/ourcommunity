import { useState, type FormEvent } from 'react'
import { Eye, EyeOff, ArrowRight } from 'lucide-react'
import { Navigate, useSearchParams } from 'react-router-dom'
import { BROWSER_DEMO } from '../demo/storage'
import { useSession } from '../lib/session'
import { useMutation, useTitle } from '../lib/hooks'
import { safeNext } from '../lib/format'
import { Button, ErrorState, Field, Loading, focusInvalid } from '../components/ui'
export function Auth() {
  useTitle('함께할 공간에 들어가기')
  const { session, loading, error, refresh, login } = useSession()
  const [search] = useSearchParams()
  const [register, setRegister] = useState(false)
  const [show, setShow] = useState(false)
  const [fields, setFields] = useState<Record<string, string>>({})
  const action = useMutation()
  const preview = !!session.preview?.enabled
  if (loading) return <Loading/>
  if (error) return <main className="auth-error"><ErrorState message={error} retry={() => void refresh()}/></main>
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
  return <main className="auth-page"><section className="auth-story"><span className="wordmark"><span className="brand-mark">o.</span>ourcommunity</span><div><p className="eyebrow">대화하고, 만나고, 함께 만드는 크루</p><h1>함께할 다음 이야기가<br/>여기 있어요.</h1><p>크루의 대화와 모임, 함께 만든 공간을 한곳에서.</p></div><div className="entry-flow"><span>대화 나누기</span><ArrowRight size={18}/><span>모임 참여</span><ArrowRight size={18}/><span>공간 키우기</span></div></section>
    <section className="auth-form"><div className="auth-form-inner"><p className="eyebrow">OUR CLUBROOM</p><h2>{register ? '함께 부를 이름을 알려주세요' : '크루 체험 시작하기'}</h2><p className="muted">{preview ? '체험 전용 · 가상 데이터입니다. 멤버로 대화하고 모임에 참여해 보세요.' : '로컬에서 실행하는 첫 제품입니다. 실제 개인정보 대신 테스트 정보를 사용해 주세요.'}</p>
      {error && <ErrorState message={error} retry={() => void refresh()}/>} {preview && action.error && <ErrorState message={action.error}/>} {!preview && <><form noValidate onSubmit={submit}>
      {register && <Field label="이름" name="display_name" error={fields.display_name}><input id="display_name" name="display_name" maxLength={30} autoComplete="nickname" aria-invalid={!!fields.display_name} aria-describedby={fields.display_name ? 'display_name-error' : undefined}/></Field>}
      <Field label="아이디" name="username" error={fields.username}><input id="username" name="username" autoComplete="username" maxLength={40} aria-invalid={!!fields.username} aria-describedby={fields.username ? 'username-error' : undefined}/></Field>
      <Field label="비밀번호" name="password" error={fields.password}><div className="password-field"><input id="password" name="password" type={show ? 'text' : 'password'} autoComplete={register ? 'new-password' : 'current-password'} maxLength={128} aria-invalid={!!fields.password} aria-describedby={fields.password ? 'password-error' : undefined}/><button type="button" aria-label={show ? '비밀번호 숨기기' : '비밀번호 보기'} onClick={() => setShow(!show)}>{show ? <EyeOff size={19}/> : <Eye size={19}/>}</button></div></Field>
      {action.error && <ErrorState compact message={action.error}/>}<Button type="submit" busy={action.busy} className="full-width">{register ? '로컬 계정 만들기' : '로그인'}<ArrowRight size={18}/></Button></form>
      <Button variant="ghost" className="full-width" onClick={() => { setRegister(!register); setFields({}); action.setError('') }}>{register ? '이미 계정이 있어요 · 로그인' : '처음이에요 · 로컬 계정 만들기'}</Button></>}
      {session.demo && <div className="demo-login"><span>{preview ? '가상 역할 선택 · 실제 계정 로그인이 아니에요' : '샘플 크루 체험하기'}</span><div><Button busy={action.busy} onClick={() => void action.run(() => login('demo', { persona: 'sora' }))}>멤버로 둘러보기</Button><Button variant="secondary" busy={action.busy} onClick={() => void action.run(() => login('demo', { persona: 'mira' }))}>운영자로 둘러보기</Button></div><small>{BROWSER_DEMO ? '같은 주소·브라우저에서 기록이 이어져요. 비공개 모드 종료, 브라우저의 저장소 정리나 체험 초기화 시 지워질 수 있어요.' : preview ? `이 브라우저만의 공간이에요. 역할을 바꿔도 기록이 이어지고, 첫 방문 1시간 뒤${session.preview?.restart_resets !== false ? ' 또는 서버 재시작 때' : ''} 초기화돼요. 다른 방문자와 초대·공유되지 않아요.` : '가상의 인물과 데이터예요. 외부 계정·푸시는 연결되지 않았어요.'}</small></div>}
    </div></section></main>
}
