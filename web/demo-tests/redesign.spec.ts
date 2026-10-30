import { test, expect, type Page } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'
import { mkdir, writeFile } from 'node:fs/promises'
const evidence = '../docs/design-docs/ourcommunity-redesign/after'
async function enter(page: Page, owner = false) {
  await page.goto('/groups/hangang/space')
  await page.getByRole('button', { name: owner ? '운영자로 둘러보기' : '멤버로 둘러보기' }).click()
  await expect(page.getByRole('heading', { name: '한강 새벽 러너스.' })).toBeVisible()
}
async function fits(page: Page, selector: string) {
  await expect(page.locator(selector)).toBeVisible()
  await page.evaluate(() => document.fonts.ready)
  const box = await page.locator(selector).boundingBox(), nav = await page.locator('.sidebar').boundingBox()
  expect(box).not.toBeNull(); expect(box!.y).toBeGreaterThanOrEqual(0)
  expect(box!.y + box!.height).toBeLessThanOrEqual(page.viewportSize()!.width < 900 ? nav!.y : page.viewportSize()!.height)
  expect(box!.height).toBeGreaterThanOrEqual(44)
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBeTruthy()
  return box
}
test('composer stays in viewport at desktop, mobile, narrow and short sizes; keyboard and scroll', async ({ page }) => {
  const metrics = []
  await enter(page)
  for (const [name, width, height] of [['desktop',1180,757],['mobile',390,844],['narrow',320,780],['short',390,500]] as const) {
    await page.setViewportSize({ width, height }); await page.goto('/groups/hangang/chat')
    await expect(page.locator('#message')).toBeVisible()
    const box = await fits(page, '#message'); await fits(page, 'button[aria-label="메시지 보내기"]')
    await page.locator('#message').focus(); await page.keyboard.press('Tab'); await expect(page.getByRole('button', { name: '메시지 보내기' })).toBeFocused()
    expect(await page.getByRole('button', { name: '메시지 보내기' }).evaluate(e => getComputedStyle(e).outlineStyle)).toBe('solid')
    metrics.push({name,width,height,composer:box})
    await mkdir(evidence,{recursive:true});await page.screenshot({path:`${evidence}/${name}-chat.png`})
    const axe = await new AxeBuilder({ page }).withTags(['wcag2a','wcag2aa','wcag21aa']).analyze(); expect(axe.violations).toEqual([])
  }
  await page.setViewportSize({width:390,height:844})
  for(let i=0;i<8;i++){await page.locator('#message').fill(`스크롤 검증 ${i} 줄바꿈과 긴 이야기를 함께 남겨요.\n입력창은 계속 보여요.`);await page.getByRole('button',{name:'메시지 보내기'}).click();await expect(page.locator('#message')).toHaveValue('')}
  await page.locator('.chat-log').evaluate(e=>{e.scrollTop=0});await fits(page,'#message')
  expect(await page.locator('.chat-log').evaluate(e=>e.scrollHeight>e.clientHeight)).toBeTruthy()
  await writeFile(`${evidence}/metrics.json`,JSON.stringify(metrics,null,2)+'\n')
})
test('entry and home participation are visible and usable without scrolling', async ({ page }) => {
  for(const [name,width,height] of [['mobile',390,844],['desktop',1180,757]] as const){
    await page.setViewportSize({width,height});await page.goto('/auth'); await expect(page.getByRole('button',{name:'멤버로 둘러보기'}).or(page.getByRole('heading',{name:'한강 새벽 러너스.'}))).toBeVisible()
    if(await page.getByRole('button',{name:'멤버로 둘러보기'}).count()){
      const entry=await page.getByRole('button',{name:'멤버로 둘러보기'}).boundingBox();expect(entry!.y+entry!.height).toBeLessThan(height)
      await page.screenshot({path:`${evidence}/${name}-entry.png`});await page.getByRole('button',{name:'멤버로 둘러보기'}).click()
    }
    await page.goto('/groups/hangang/space');await expect(page.locator('.home-meeting')).toBeVisible();await fits(page,'.home-meeting .button')
    await page.screenshot({path:`${evidence}/${name}-space.png`})
    await page.goto('/groups/hangang/events/1');await expect(page.locator('.event-actions')).toBeVisible();await fits(page,'.event-actions .button.primary')
    await page.screenshot({path:`${evidence}/${name}-events-1.png`})
  }
  await page.goto('/groups/hangang/space');await page.getByRole('button',{name:'참가 신청',exact:true}).click();await expect(page.getByRole('link',{name:'신청 확인'})).toBeVisible()
  await page.reload();await expect(page.getByRole('link',{name:'신청 확인'})).toBeVisible()
  await page.getByRole('link',{name:'신청 확인'}).click();await expect(page.getByText('모임에서 만나요!',{exact:true})).toBeVisible()
})
test('version 1 records survive, unlocked shared objects move persistently and member cannot arrange', async ({ page }) => {
  await enter(page,true)
  await page.goto('/groups/hangang/events/2');await page.locator('.member-row').filter({has:page.getByText('지호',{exact:true})}).getByRole('button',{name:'출석 확인',exact:true}).click()
  await page.goto('/groups/hangang/memories');await expect(page.locator('.asset-item.earned')).toHaveCount(2)
  await page.getByRole('button',{name:'잠깐 쉬어 가는 벤치 살펴보기'}).click();await page.getByRole('button',{name:'정원',exact:true}).click()
  await expect(page.getByRole('status').filter({hasText:'기념물 위치를 저장'})).toBeVisible();await expect(page.locator('.space-object.slot-garden')).toContainText('벤치')
  await page.reload();await expect(page.locator('.space-object.slot-garden')).toContainText('벤치');await expect(page.locator('.asset-item.earned')).toHaveCount(2)
  await page.screenshot({path:`${evidence}/mobile-arranged.png`})
  await page.getByRole('button',{name:'함께 자라는 기억나무 만드는 방법 보기'}).click();await expect(page.getByRole('button',{name:'입구',exact:true})).toHaveCount(0)
  // The old v1 schema lacks the optional layout. Removing it must retain attendance and other records.
  await page.evaluate(()=>new Promise<void>((resolve,reject)=>{const r=indexedDB.open('ourcommunity-browser-demo-v1',1);r.onsuccess=()=>{const db=r.result,tx=db.transaction('demo','readwrite'),s=tx.objectStore('demo'),q=s.get('state');q.onsuccess=()=>{delete q.result.space_layout;s.put(q.result,'state')};tx.oncomplete=()=>{db.close();resolve()};tx.onerror=()=>reject(tx.error)}}))
  await page.reload();await expect(page.locator('.space-object.slot-center')).toContainText('벤치');await expect(page.locator('.asset-item.earned')).toHaveCount(2)
  await page.getByRole('button',{name:'계정과 로그아웃'}).click();await page.getByRole('button',{name:'역할 다시 선택'}).click();await page.getByRole('button',{name:'멤버로 둘러보기'}).click()
  await page.goto('/groups/hangang/memories');await page.getByRole('button',{name:'잠깐 쉬어 가는 벤치 살펴보기'}).click();await expect(page.getByRole('button',{name:'정원',exact:true})).toHaveCount(0)
})

test('local space adapter rejects member, locked asset, stale version and invalid mutation without partial writes', async ({ page }) => {
  await enter(page)
  // Bypass button visibility through the shipped adapter; no test-only production hook.
  const call = (path: string, method = 'GET', data?: Record<string,unknown>) => page.evaluate(async ({path,method,data}) => {
    const moduleUrl = performance.getEntriesByType('resource').map(e=>e.name).find(url=>/\/assets\/api-[^/]+\.js$/.test(url))
    if(!moduleUrl) throw new Error('Browser demo adapter did not load')
    const {demoApi} = await import(moduleUrl)
    try { return { status: 200, value: await demoApi(path,{method,body:data ? JSON.stringify(data) : undefined}) } }
    catch(error) { return {status:(error as {status:number}).status,value:null} }
  },{path,method,data})
  const original = await call('/groups/hangang')
  expect((await call('/groups/hangang/space','PATCH',{asset_id:'trail-sign',slot:'garden',version:original.value.version})).status).toBe(403)
  await call('/auth/demo','POST',{persona:'mira'})
  expect((await call('/groups/hangang/space','PATCH',{asset_id:'bench',slot:'garden',version:original.value.version})).status).toBe(403)
  expect((await call('/groups/hangang/space','GET',{asset_id:'trail-sign',slot:'garden',version:original.value.version})).status).toBe(405)
  expect((await call('/groups/hangang/space','PATCH',{asset_id:'trail-sign',slot:'outside',version:original.value.version})).status).toBe(400)
  const changed = await call('/groups/hangang/space','PATCH',{asset_id:'trail-sign',slot:'garden',version:original.value.version})
  expect(changed.status).toBe(200);expect(changed.value.space_layout['trail-sign']).toBe('garden')
  expect((await call('/groups/hangang/space','PATCH',{asset_id:'trail-sign',slot:'center',version:original.value.version})).status).toBe(409)
  const final = await call('/groups/hangang');expect(final.value.version).toBe(original.value.version+1);expect(final.value.space_layout['trail-sign']).toBe('garden')
})

test('short viewport keeps blocked-storage warning visible', async ({ page }) => {
  await page.setViewportSize({width:390,height:500})
  await page.addInitScript(()=>{Object.defineProperty(window,'indexedDB',{get:()=>{throw new DOMException('blocked','SecurityError')}})})
  await enter(page);await page.goto('/groups/hangang/chat');await page.getByRole('button',{name:'멤버로 둘러보기'}).click()
  await expect(page.getByRole('alert').filter({hasText:'이번 화면에서만 체험'})).toBeVisible();await fits(page,'#message')
})
