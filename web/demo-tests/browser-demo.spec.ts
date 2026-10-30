import { test, expect, type Page } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'
test.beforeEach(async ({ request }) => {
  const marker = await request.get('/demo-build.json')
  expect(marker.ok()).toBeTruthy()
  expect(await marker.json()).toMatchObject({ mode: 'browser-only-demo', api: false })
})
async function member(page: Page, path = '/groups/hangang/chat') { await page.goto(path); await page.getByRole('button', { name: '멤버로 둘러보기' }).click(); await expect(page.getByRole('heading', { name: '크루 대화' })).toBeVisible() }
async function owner(page: Page) { await page.getByRole('button', { name: '계정과 로그아웃' }).click(); await page.getByRole('button', { name: '역할 다시 선택' }).click(); await page.getByRole('button', { name: '운영자로 둘러보기' }).click(); await expect(page.getByRole('button', { name: '계정과 로그아웃' })).toBeVisible() }
async function send(page: Page, message: string) { await page.getByRole('textbox', { name: '메시지', exact: true }).fill(message); await page.getByRole('button', { name: '메시지 보내기' }).click(); await expect(page.getByText(message, { exact: true })).toBeVisible() }

test('static mobile journey, reload/reopen, attendance growth, isolation and zero API calls', async ({ page, context, browser }) => {
  const failures: string[] = [], apiCalls: string[] = []
  page.on('pageerror', error => failures.push(error.message))
  context.on('request', request => { if (new URL(request.url()).pathname.startsWith('/api/')) apiCalls.push(request.url()) })
  await member(page)
  await expect(page.getByText('브라우저 체험 · 가상 인물과 시연 대화', { exact: true })).toBeVisible()
  await send(page, '이 브라우저에만 남기는 안부')
  await page.reload(); await expect(page.getByText('이 브라우저에만 남기는 안부', { exact: true })).toBeVisible()
  const reopened = await context.newPage(); await reopened.goto('/groups/hangang/chat'); await expect(reopened.getByText('이 브라우저에만 남기는 안부', { exact: true })).toBeVisible(); await reopened.close()
  await page.goto('/groups/hangang/events/1'); await page.getByRole('button', { name: '참가 신청', exact: true }).click(); await expect(page.getByText('모임에서 만나요!', { exact: true })).toBeVisible()
  await page.getByRole('button', { name: '신청 취소', exact: true }).click(); await page.getByRole('button', { name: '돌아가기', exact: true }).click(); await expect(page.getByText('모임에서 만나요!', { exact: true })).toBeVisible()
  await page.getByRole('button', { name: '신청 취소', exact: true }).click(); await page.getByRole('dialog').getByRole('button', { name: '신청 취소', exact: true }).click(); await expect(page.getByRole('button', { name: '참가 신청', exact: true })).toBeVisible()
  await owner(page); await page.goto('/groups/hangang/events/2')
  const jiho = page.locator('.member-row').filter({ has: page.getByText('지호', { exact: true }) })
  await jiho.getByRole('button', { name: '출석 확인', exact: true }).click(); await expect(jiho.getByRole('button', { name: '출석 수정' })).toBeVisible()
  await page.goto('/groups/hangang/memories'); await expect(page.locator('.asset-item.earned')).toHaveCount(2)
  await expect(page.locator('.asset-item').filter({ hasText: '잠깐 쉬어 가는 벤치' })).toContainText('3 / 3')
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBeTruthy()
  await page.screenshot({ path: 'demo-test-results/browser-demo-mobile.png', fullPage: true })
  const axe = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze(); expect(axe.violations).toEqual([])
  await page.setViewportSize({ width: 1440, height: 1000 }); await page.goto('/groups/hangang/space'); await expect(page.getByRole('heading', { name: '한강 새벽 러너스.' })).toBeVisible(); await page.screenshot({ path: 'demo-test-results/browser-demo-desktop.png', fullPage: true })
  const separate = await browser.newContext({ baseURL: test.info().project.use.baseURL }); const other = await separate.newPage(); await member(other); await expect(other.getByText('이 브라우저에만 남기는 안부', { exact: true })).toHaveCount(0); await separate.close()
  expect(apiCalls).toEqual([]); expect(failures).toEqual([])
})

test('reset cancel/Escape preserves data, confirmation restores sample', async ({ page }) => {
  await member(page); await send(page, '초기화 전 기록')
  await page.getByRole('button', { name: '체험 초기화', exact: true }).click(); await page.keyboard.press('Escape'); await expect(page.getByText('초기화 전 기록', { exact: true })).toBeVisible()
  await page.getByRole('button', { name: '체험 초기화', exact: true }).click(); await page.getByRole('button', { name: '돌아가기', exact: true }).click(); await expect(page.getByText('초기화 전 기록', { exact: true })).toBeVisible()
  await page.getByRole('button', { name: '체험 초기화', exact: true }).click(); await page.getByRole('button', { name: '기록 지우고 다시 시작' }).click()
  await expect(page.getByRole('button', { name: '멤버로 둘러보기' })).toBeVisible(); await member(page); await expect(page.getByText('초기화 전 기록', { exact: true })).toHaveCount(0)
})

test('blocked storage remains usable with explicit temporary notice', async ({ page }) => {
  await page.addInitScript(() => { Object.defineProperty(window, 'indexedDB', { get: () => { throw new DOMException('blocked', 'SecurityError') } }) })
  await member(page); await expect(page.getByRole('alert').filter({ hasText: '이번 화면에서만 체험' })).toBeVisible(); await send(page, '이번 화면에서만 유지')
  await page.reload(); await expect(page.getByRole('button', { name: '멤버로 둘러보기' })).toBeVisible(); await page.getByRole('button', { name: '멤버로 둘러보기' }).click(); await expect(page.getByText('이번 화면에서만 유지', { exact: true })).toHaveCount(0)
})

test('quota failure keeps draft and committed state, retry saves once', async ({ page }) => {
  await member(page)
  await page.evaluate(() => {
    const original = IDBObjectStore.prototype.put
    IDBObjectStore.prototype.put = function(value, key) { if (JSON.stringify(value).includes('저장 실패 뒤 재시도')) throw new DOMException('quota', 'QuotaExceededError'); return key === undefined ? original.call(this, value) : original.call(this, value, key) }
    Object.assign(window, { restorePut: () => { IDBObjectStore.prototype.put = original } })
  })
  await page.getByRole('textbox', { name: '메시지', exact: true }).fill('저장 실패 뒤 재시도'); await page.getByRole('button', { name: '메시지 보내기' }).click()
  await expect(page.getByRole('alert').filter({ hasText: '저장하지 못했어요' })).toBeVisible(); await expect(page.getByRole('textbox', { name: '메시지', exact: true })).toHaveValue('저장 실패 뒤 재시도'); await expect(page.locator('.message').filter({ hasText: '저장 실패 뒤 재시도' })).toHaveCount(0)
  await page.evaluate(() => (window as unknown as { restorePut: () => void }).restorePut())
  await page.getByRole('button', { name: '메시지 보내기' }).click(); await expect(page.locator('.message').filter({ hasText: '저장 실패 뒤 재시도' })).toHaveCount(1); await page.reload(); await expect(page.locator('.message').filter({ hasText: '저장 실패 뒤 재시도' })).toHaveCount(1)
})

test('corrupted record shows recovery and reset works', async ({ page }) => {
  await member(page)
  await page.evaluate(() => new Promise<void>((resolve, reject) => { const request = indexedDB.open('ourcommunity-browser-demo-v1', 1); request.onsuccess = () => { const db = request.result, tx = db.transaction('demo', 'readwrite'); tx.objectStore('demo').put({ version: 99 }, 'state'); tx.oncomplete = () => { db.close(); resolve() }; tx.onerror = () => reject(tx.error) } }))
  await page.reload(); await expect(page.getByRole('alert').filter({ hasText: '체험 기록을 읽을 수 없어요' })).toBeVisible()
  await page.getByRole('button', { name: '체험 초기화', exact: true }).click(); await page.getByRole('button', { name: '기록 지우고 다시 시작' }).click(); await expect(page.getByRole('button', { name: '멤버로 둘러보기' })).toBeVisible()
})

test('create/cancel event, announcement, member boundary, unsaved back navigation', async ({ page }) => {
  await member(page); await page.goto('/groups/hangang/events/new'); await expect(page.getByRole('alert')).toContainText('운영자가')
  await owner(page); await page.goto('/groups/hangang/events/new'); await page.getByLabel('모임 이름', { exact: true }).fill('작성 중인 시연 모임'); await page.getByRole('button', { name: '취소', exact: true }).click(); await expect(page.getByRole('dialog')).toContainText('작성 중인 내용'); await page.getByRole('button', { name: '돌아가기', exact: true }).click(); await expect(page.getByLabel('모임 이름', { exact: true })).toHaveValue('작성 중인 시연 모임')
  await page.getByLabel('만날 장소', { exact: true }).fill('시연 공원'); await page.getByRole('button', { name: '모임 만들기', exact: true }).click(); await expect(page.getByRole('heading', { name: '작성 중인 시연 모임' })).toBeVisible()
  await page.getByRole('button', { name: '모임 전체 취소' }).click(); await page.getByRole('button', { name: '모임 취소', exact: true }).click(); await expect(page.getByText('운영자가 취소한 모임이에요.')).toBeVisible()
  await page.goto('/groups/hangang/chat'); await page.getByRole('button', { name: '공지', exact: true }).click(); await page.getByRole('dialog').getByRole('button', { name: '공지 올리기', exact: true }).click(); await page.getByLabel('공지 내용').fill('브라우저 안의 시연 공지'); await page.getByRole('dialog').getByRole('button', { name: '공지 올리기', exact: true }).click(); await expect(page.getByRole('dialog')).not.toBeVisible(); await page.getByRole('button', { name: '공지', exact: true }).click(); await expect(page.getByRole('dialog').getByText('브라우저 안의 시연 공지', { exact: true })).toBeVisible(); await page.keyboard.press('Escape')
  await page.goto('/groups/seongsu/chat'); await expect(page.getByRole('alert')).toContainText('접근할 수 없어요')
})

test('waitlist promotes after member removal and requires explicit acceptance', async ({ page }) => {
  await member(page); await page.goto('/groups/hangang/events/3'); await page.getByRole('button', { name: '대기 신청', exact: true }).click(); await expect(page.getByText('빈자리를 기다리고 있어요.', { exact: true })).toBeVisible()
  await owner(page); await page.goto('/groups/hangang/settings')
  await expect(page.getByRole('button', { name: '집계 미연결' })).toBeDisabled()
  await page.locator('.member-row').filter({ has: page.getByText('지호', { exact: true }) }).getByRole('button', { name: '내보내기' }).click()
  await page.getByRole('dialog').getByRole('button', { name: '내보내기', exact: true }).click(); await expect(page.getByRole('dialog')).not.toBeVisible()
  await page.goto('/groups/hangang/events/2')
  await page.locator('.member-row').filter({ has: page.getByText('지호', { exact: true }) }).getByRole('button', { name: '출석 확인', exact: true }).click()
  await expect(page.getByRole('alert')).toContainText('현재 크루 멤버의 출석만')
  await page.getByRole('button', { name: '계정과 로그아웃' }).click(); await page.getByRole('button', { name: '역할 다시 선택' }).click(); await page.getByRole('button', { name: '멤버로 둘러보기' }).click(); await expect(page.getByRole('button', { name: '계정과 로그아웃' })).toBeVisible()
  await page.goto('/groups/hangang/events/3'); await page.getByRole('button', { name: '참가 확정하기' }).click(); await expect(page.getByText('모임에서 만나요!', { exact: true })).toBeVisible(); await expect(page.getByText('2명 참가 · 정원 2명')).toBeVisible()
})

test('two tabs commit without dropping messages and share reset', async ({ page, context }) => {
  await member(page)
  const second = await context.newPage(); await second.goto('/groups/hangang/chat'); await expect(second.getByRole('heading', { name: '크루 대화' })).toBeVisible()
  await Promise.all([send(page, '첫 탭의 시연 메시지'), send(second, '둘째 탭의 시연 메시지')])
  await page.reload(); await expect(page.getByText('첫 탭의 시연 메시지', { exact: true })).toBeVisible(); await expect(page.getByText('둘째 탭의 시연 메시지', { exact: true })).toBeVisible()
  await second.getByRole('button', { name: '체험 초기화', exact: true }).click(); await second.getByRole('button', { name: '기록 지우고 다시 시작' }).click(); await page.reload(); await expect(page.getByRole('button', { name: '멤버로 둘러보기' })).toBeVisible(); await second.close()
})
