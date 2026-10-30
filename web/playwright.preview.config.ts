import { defineConfig } from '@playwright/test'
const origin = process.env.PREVIEW_TEST_ORIGIN || 'http://127.0.0.1:8088'
export default defineConfig({
  testDir: './preview-tests', workers: 1, timeout: 45000,
  expect: { timeout: 10000 }, reporter: [['list']],
  use: { baseURL: origin, viewport: { width: 390, height: 844 },
    locale: 'ko-KR', timezoneId: 'Asia/Seoul',
    launchOptions: { executablePath: '/usr/bin/chromium', args: ['--no-sandbox'] },
    trace: 'retain-on-failure', screenshot: 'only-on-failure' },
  webServer: process.env.PREVIEW_TEST_EXTERNAL === '1' ? undefined : { command: 'PREVIEW_MODE=1 PUBLIC_ORIGIN=http://127.0.0.1:8088 .venv/bin/uvicorn community.app:app --host 127.0.0.1 --port 8088 --workers 1',
    cwd: '..', url: 'http://127.0.0.1:8088/api/health', reuseExistingServer: false }
})
