import { test, expect } from '@playwright/test'

test('home preserves the last shared space but exposes failed refresh and retry', async ({ page }) => {
  await page.goto('/auth')
  const login = await page.request.post('/api/auth/demo', {headers:{Origin:'http://127.0.0.1:5173'},data:{persona:'sora'}})
  expect(login.ok()).toBeTruthy()
  let fail = false
  await page.route('**/api/groups/hangang/growth', async route => {
    if(fail) await route.fulfill({status:503,contentType:'application/json',body:JSON.stringify({detail:'시연 성장 조회 일시 실패'})})
    else await route.continue()
  })
  await page.goto('/groups/hangang/space');await expect(page.locator('.home-shared-space .space-map')).toBeVisible()
  fail = true;await page.evaluate(()=>window.dispatchEvent(new Event('online')))
  const alert = page.locator('.home-shared-space').getByRole('alert')
  await expect(alert).toContainText('공동 공간을 갱신하지 못했어요')
  await expect(page.locator('.home-shared-space .space-map')).toBeVisible()
  fail = false;await alert.getByRole('button',{name:'다시 시도'}).click();await expect(alert).toHaveCount(0)
  await expect(page.locator('.home-shared-space .space-map')).toBeVisible()
})
