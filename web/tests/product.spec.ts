import { expect, test, type BrowserContext, type Page } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'
import { mkdir } from 'node:fs/promises'
import path from 'node:path'

const screenshots = path.resolve(process.cwd(), '../docs/implementation/screenshots')
const unique = (prefix: string) => `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2,7)}`
async function demo(page: Page, persona = 'mira') {
  await page.goto('/auth')
  const response = await page.request.post('/api/auth/demo', { headers: { Origin: 'http://127.0.0.1:5173' }, data: { persona } })
  expect(response.ok()).toBeTruthy()
  await page.goto('/groups/hangang/space')
  await expect(page.getByRole('heading', { name: '한강 새벽 러너스.' })).toBeVisible()
}
async function command(context: BrowserContext, endpoint: string, data?: unknown, method = 'POST') {
  const session = await (await context.request.get('/api/session')).json()
  return context.request.fetch(`/api${endpoint}`, { method, headers: { Origin: 'http://127.0.0.1:5173', 'X-CSRF-Token': session.csrf }, data })
}
async function capture(page: Page, name: string) { await mkdir(screenshots, { recursive: true }); await page.screenshot({ path: path.join(screenshots, name), fullPage: true }) }
async function accessible(page: Page) {
  await page.evaluate(() => document.fonts.ready)
  const results = await new AxeBuilder({ page }).analyze()
  expect(results.violations.map(item => ({ id: item.id, nodes: item.nodes.map(node => node.target) }))).toEqual([])
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBeTruthy()
}

test('desktop/mobile clubhouse, route navigation and accessibility', async ({ page }) => {
  const errors: string[] = []; page.on('pageerror', error => errors.push(error.message))
  await demo(page)
  await accessible(page); await capture(page, 'desktop-space.png')
  await page.setViewportSize({ width: 390, height: 844 })
  await accessible(page); await capture(page, 'mobile-space.png')
  for (const route of ['chat', 'events', 'memories', 'settings']) {
    await page.goto(`/groups/hangang/${route}`)
    await expect(page.locator('h1')).toBeVisible()
    await accessible(page)
    if (route === 'chat') {
      const send = await page.getByRole('button', { name: '메시지 보내기' }).boundingBox()
      const navigation = await page.locator('.sidebar').boundingBox()
      expect(send!.y + send!.height).toBeLessThanOrEqual(navigation!.y)
    }
    await capture(page, `mobile-${route}.png`)
  }
  await page.setViewportSize({ width: 320, height: 780 }); await page.goto('/groups/hangang/space'); await expect(page.locator('h1')).toBeVisible(); await accessible(page)
  await page.emulateMedia({ reducedMotion: 'reduce' })
  expect(await page.locator('.sidebar').evaluate(element => getComputedStyle(element).animationName)).toBe('none')
  expect(errors).toEqual([])
})

test('message persistence, lost acknowledgement retry, dirty navigation and deletion', async ({ page, context }) => {
  await demo(page, 'sora'); await page.getByRole('link', { name: '대화', exact: true }).click()
  const body = unique('재전송 확인')
  await page.getByLabel('메시지', { exact: true }).fill(body)
  let dropped = false
  await page.route('**/api/groups/hangang/messages', async route => {
    if (route.request().method() === 'POST' && !dropped) { dropped = true; await route.fetch(); await route.abort('failed') }
    else await route.continue()
  })
  await page.getByRole('button', { name: '메시지 보내기' }).click()
  await expect(page.getByRole('alert')).toContainText('연결이 잠시 끊겼어요')
  await expect(page.getByLabel('메시지', { exact: true })).toHaveValue(body)
  await page.getByRole('button', { name: '메시지 보내기' }).click()
  await expect(page.getByLabel('메시지', { exact: true })).toHaveValue('')
  await expect(page.locator('.message-content>p').filter({ hasText: body })).toHaveCount(1)
  const data = await (await context.request.get('/api/groups/hangang/messages?limit=200')).json()
  expect(data.items.filter((item: { body: string }) => item.body === body)).toHaveLength(1)
  await page.unroute('**/api/groups/hangang/messages')
  await page.getByLabel('메시지', { exact: true }).fill('아직 보내지 않은 안부')
  await page.getByRole('link', { name: '모임', exact: true }).click()
  await expect(page.getByRole('dialog', { name: '작성 중인 내용이 있어요' })).toBeVisible()
  await page.getByRole('button', { name: '돌아가기', exact: true }).click()
  await expect(page.getByLabel('메시지', { exact: true })).toHaveValue('아직 보내지 않은 안부')
  await page.getByLabel('메시지', { exact: true }).fill('')
  const row = page.locator('article.message').filter({ hasText: body })
  await row.getByRole('button', { name: '수아 메시지 메뉴' }).click()
  await page.getByRole('button', { name: '메시지 삭제', exact: true }).click()
  await page.getByRole('button', { name: '돌아가기', exact: true }).click()
  await expect(page.locator('.message-content>p').filter({ hasText: body })).toHaveCount(1)
  await row.getByRole('button', { name: '수아 메시지 메뉴' }).click(); await page.getByRole('button', { name: '메시지 삭제', exact: true }).click(); await page.getByRole('button', { name: '삭제', exact: true }).click()
  await expect(page.locator('.message-content>p').filter({ hasText: body })).toHaveCount(0)
  await page.reload(); await expect(page.getByText('삭제된 메시지예요.').first()).toBeVisible()
})

test('create event, field errors, KST interpretation, RSVP and cancellation', async ({ page, browser }) => {
  await demo(page); await page.getByRole('link', { name: '모임', exact: true }).click(); await page.getByRole('link', { name: '모임 만들기' }).click()
  await page.getByRole('button', { name: '모임 만들기' }).click()
  await expect(page.getByLabel('모임 이름')).toBeFocused()
  await expect(page.getByText('모임 이름을 2자 이상 입력해 주세요.')).toBeVisible()
  const name = unique('함께 달리는 테스트')
  await page.getByLabel('모임 이름').fill(name); await page.getByLabel('함께할 이야기').fill('실제 예약이 아닌 로컬 검증 모임입니다.'); await page.getByLabel('만날 장소').fill('테스트 강가')
  await page.getByLabel('함께할 정원').fill('2')
  const inputTime = await page.getByLabel('시작 · 한국 시간').inputValue()
  await page.getByRole('button', { name: '모임 만들기' }).click()
  await expect(page.getByRole('heading', { name, exact: true })).toBeVisible()
  const eventId = page.url().split('/').at(-1)
  const detail = await (await page.request.get(`/api/events/${eventId}`)).json()
  expect(new Date(detail.starts_at).getTime()).toBe(new Date(`${inputTime}:00+09:00`).getTime())
  await accessible(page); await capture(page, 'desktop-event-detail.png')
  const memberContext = await browser.newContext({ baseURL: 'http://127.0.0.1:5173', viewport: { width: 390, height: 844 } }); const member = await memberContext.newPage()
  await demo(member, 'sora'); await member.goto(`/groups/hangang/events/${eventId}`)
  await member.getByRole('button', { name: '참가 신청', exact: true }).click(); await expect(member.getByText('모임에서 만나요!')).toBeVisible()
  await member.getByRole('button', { name: '신청 취소', exact: true }).click(); await member.getByRole('button', { name: '돌아가기', exact: true }).click(); await expect(member.getByText('모임에서 만나요!')).toBeVisible()
  await member.getByRole('button', { name: '신청 취소', exact: true }).click(); await member.getByRole('dialog').getByRole('button', { name: '신청 취소', exact: true }).click(); await expect(member.getByRole('button', { name: '참가 신청', exact: true })).toBeVisible()
  await member.goBack(); await expect(member.getByRole('heading', { name: '한강 새벽 러너스.' })).toBeVisible()
  await memberContext.close()
  await page.getByRole('button', { name: '모임 전체 취소' }).click(); await page.getByRole('button', { name: '모임 취소', exact: true }).click(); await expect(page.getByText('운영자가 취소한 모임이에요.')).toBeVisible()
})

test('announcement, explicit public privacy choice and reversible attendance growth', async ({ page, context }) => {
  await demo(page)
  await page.goto('/groups/hangang/chat'); await page.getByRole('button', { name: '공지 올리기', exact: true }).click()
  const body = unique('우리의 새 공지'); await page.getByLabel('공지 내용').fill(body); await page.getByRole('dialog').getByRole('button', { name: '공지 올리기' }).click(); await expect(page.getByText(body, { exact: true })).toBeVisible()
  await page.goto('/groups/hangang/settings'); await page.getByRole('button', { name: '비공개', exact: true }).click(); await page.getByRole('button', { name: '돌아가기', exact: true }).click(); await expect(page.getByRole('button', { name: '비공개', exact: true })).toBeVisible()
  await page.getByRole('button', { name: '비공개', exact: true }).click(); await page.getByRole('button', { name: '선택 적용' }).click(); await expect(page.getByRole('button', { name: '공개 중', exact: true })).toBeVisible()
  try {
    const publicView = await (await context.request.get('/api/public/groups/hangang')).json()
    expect(Object.keys(publicView).sort()).toEqual(['assets','description','id','name','palette','recent'])
    expect(publicView.recent.visible).toBe(false)
    await page.getByRole('link', { name: '공개 공간 확인' }).click(); await expect(page.getByText('대화는 멤버들끼리만.', { exact: false })).toBeVisible(); await accessible(page); await capture(page, 'public-space.png')
  } finally {
    const group = await (await context.request.get('/api/groups/hangang')).json()
    await command(context, '/groups/hangang/settings', { version: group.version, public_space: false }, 'PATCH')
  }
  const events = await (await context.request.get('/api/groups/hangang/events')).json()
  const past = events.items.find((item: { title: string }) => item.title.startsWith('지난 모임'))
  await page.goto(`/groups/hangang/events/${past.id}`)
  const changed: string[] = []
  try {
    for (const name of ['지호', '유나']) {
      const row = page.locator('.member-row').filter({ hasText: name }); await expect(row).toBeVisible(); const button = row.getByRole('button', { name: '출석 확인', exact: true })
      if (await button.count()) { await button.click(); await expect(row.getByRole('button', { name: '출석 수정' })).toBeVisible(); changed.push(name === '지호' ? 'jiho' : 'yuna') }
    }
    await page.goto('/groups/hangang/memories'); await expect(page.getByRole('heading', { name: '함께 자라는 나무' })).toBeVisible(); const tree = page.locator('.asset-item').filter({ hasText: '함께 자라는 나무' }); await expect(tree).toContainText('우리 공간에 함께'); await capture(page, 'desktop-earned-memories.png')
  } finally { for (const user_id of changed) await command(context, `/events/${past.id}/attendance`, { user_id, present: false }) }
})

test('invite to login return, membership history and leaving blocks private access', async ({ browser }) => {
  const ownerContext = await browser.newContext({ baseURL: 'http://127.0.0.1:5173' }); const owner = await ownerContext.newPage(); await demo(owner)
  await owner.goto('/groups/hangang/settings'); await owner.getByRole('button', { name: '초대 링크 만들기' }).click(); const invite = await owner.getByLabel('초대 링크', { exact: true }).inputValue()
  const context = await browser.newContext({ baseURL: 'http://127.0.0.1:5173', viewport: { width: 390, height: 844 } }); const page = await context.newPage()
  await page.goto(invite); await page.getByRole('link', { name: '로그인하고 초대 확인하기' }).click(); await page.getByRole('button', { name: '처음이에요 · 로컬 계정 만들기' }).click()
  await page.getByLabel('이름', { exact: true }).fill('새로운 테스트 멤버'); await page.getByLabel('아이디', { exact: true }).fill(unique('test').slice(0,39)); await page.getByLabel('비밀번호', { exact: true }).fill('local-browser-test-password')
  await page.getByRole('button', { name: '로컬 계정 만들기', exact: true }).click(); await expect(page.getByRole('button', { name: '이 크루에 함께하기' })).toBeVisible(); await page.getByRole('button', { name: '이 크루에 함께하기' }).click(); await expect(page.getByRole('heading', { name: '한강 새벽 러너스.' })).toBeVisible()
  await page.getByRole('link', { name: '대화', exact: true }).click(); await expect(page.getByRole('heading', { name: '첫 이야기를 기다리고 있어요' })).toBeVisible()
  await page.getByRole('link', { name: '설정', exact: true }).click(); await page.getByRole('button', { name: '이 크루 떠나기' }).click(); await page.getByRole('button', { name: '크루 떠나기', exact: true }).click(); await expect(page.getByRole('heading', { name: '함께할 공간을 기다리고 있어요' })).toBeVisible()
  await page.goto('/groups/hangang/chat'); await expect(page.getByRole('alert')).toBeVisible(); await expect(page.locator('article.message')).toHaveCount(0)
  await context.close(); await ownerContext.close()
})

test('an older anonymous session cannot overwrite a completed login', async ({ page }) => {
  let fail = true
  let hold = false
  let held = false
  let release: (() => void) | undefined
  await page.route('**/api/session', async route => {
    if (fail) { await route.abort('failed'); return }
    const response = await route.fetch()
    if (hold && !held) { held = true; await new Promise<void>(resolve => { release = resolve }) }
    await route.fulfill({ response }).catch(() => undefined)
  })
  await page.goto('/auth'); await expect(page.getByRole('button', { name: '다시 시도' })).toBeVisible()
  fail = false; hold = true
  await page.getByRole('button', { name: '다시 시도' }).click()
  await expect.poll(() => held).toBe(true)
  await page.getByRole('button', { name: '다시 시도' }).click()
  await expect(page.getByRole('button', { name: '멤버로 둘러보기' })).toBeVisible()
  await page.getByRole('button', { name: '멤버로 둘러보기' }).click(); await expect(page.getByRole('heading', { name: '한강 새벽 러너스.' })).toBeVisible()
  release?.()
  await page.waitForTimeout(300)
  await expect(page).toHaveURL(/\/groups\/hangang\/space$/)
  await expect(page.getByRole('heading', { name: '한강 새벽 러너스.' })).toBeVisible()
})

test('loading an earlier chat page preserves draft navigation protection', async ({ page }) => {
  await demo(page, 'sora')
  let release: (() => void) | undefined
  let waiting = false
  await page.route('**/api/groups/hangang/messages?*', async route => {
    const response = await route.fetch()
    const body = await response.json()
    if (route.request().url().includes('before=')) { waiting = true; await new Promise<void>(resolve => { release = resolve }); await route.fulfill({ response }); return }
    await route.fulfill({ response, json: { ...body, has_more: true } })
  })
  await page.getByRole('link', { name: '대화', exact: true }).click()
  await page.getByLabel('메시지', { exact: true }).fill('페이지가 바뀌어도 지켜질 초안')
  await page.getByRole('button', { name: '이전 대화 50개 보기' }).click(); await expect.poll(() => waiting).toBe(true)
  await page.getByRole('link', { name: '모임', exact: true }).click(); await expect(page.getByRole('dialog', { name: '작성 중인 내용이 있어요' })).toBeVisible()
  await page.keyboard.press('Escape'); await expect(page.getByRole('dialog', { name: '작성 중인 내용이 있어요' })).not.toBeVisible()
  release?.(); await expect(page.getByLabel('메시지', { exact: true })).toHaveValue('페이지가 바뀌어도 지켜질 초안')
  await page.getByLabel('메시지', { exact: true }).fill('')
})

test('pending creation protects input and navigation until server confirmation', async ({ page }) => {
  await demo(page); await page.goto('/groups/hangang/events/new')
  const title = unique('저장 경계 확인'); await page.getByLabel('모임 이름').fill(title); await page.getByLabel('만날 장소').fill('로컬 테스트 장소')
  let release: (() => void) | undefined, pending = false
  await page.route('**/api/groups/hangang/events', async route => {
    if (route.request().method() !== 'POST') { await route.continue(); return }
    const response = await route.fetch(); pending = true; await new Promise<void>(resolve => { release = resolve }); await route.fulfill({ response })
  })
  await page.getByRole('button', { name: '모임 만들기', exact: true }).click(); await expect.poll(() => pending).toBe(true)
  await expect(page.getByLabel('모임 이름')).toBeDisabled(); await expect(page.getByRole('button', { name: '취소', exact: true })).toBeDisabled()
  await page.getByRole('link', { name: '모임', exact: true }).click(); await expect(page.getByRole('dialog', { name: '저장 결과를 확인하고 있어요' })).toBeVisible()
  await expect(page.getByRole('dialog').getByRole('button', { name: '저장 중', exact: true })).toBeDisabled()
  release?.(); await expect(page.getByRole('heading', { name: title, exact: true })).toBeVisible()
  await page.getByRole('button', { name: '모임 전체 취소' }).click(); await page.getByRole('button', { name: '모임 취소', exact: true }).click()
})

test('reporting and mutual chat blocking preserve announcement access', async ({ page, context }) => {
  await demo(page, 'sora'); await page.goto('/groups/hangang/chat')
  const response = await (await context.request.get('/api/groups/hangang/messages?limit=50')).json()
  const target = response.items.find((item: { deleted: boolean; author: { id: string } }) => !item.deleted && item.author.id === 'jun')
  expect(target).toBeTruthy()
  const row = page.locator('article.message').filter({ hasText: target.body })
  await row.getByRole('button', { name: '도현 메시지 메뉴' }).click(); await page.getByRole('button', { name: '메시지 신고', exact: true }).click(); await page.getByLabel('신고 이유').fill('로컬 브라우저 신고 흐름 검증'); await page.getByRole('button', { name: '신고 보내기' }).click(); await expect(page.getByText('신고를 운영자에게 전달했어요.')).toBeVisible()
  try {
    await row.getByRole('button', { name: '도현 메시지 메뉴' }).click(); await page.getByRole('button', { name: '이 멤버의 대화 차단' }).click(); await page.getByRole('button', { name: '대화 차단', exact: true }).click(); await expect(row).toHaveCount(0)
    await expect(page.getByRole('heading', { name: '우리의 공지' })).toBeVisible()
    await page.getByRole('link', { name: '설정', exact: true }).click(); const blocked = page.locator('.setting-row').filter({ hasText: '도현' }); await blocked.getByRole('button', { name: '차단 해제' }).click(); await expect(blocked).toHaveCount(0)
  } finally { await command(context, '/blocks/jun', undefined, 'DELETE') }
})
