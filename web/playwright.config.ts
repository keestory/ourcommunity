import { defineConfig } from '@playwright/test'
export default defineConfig({
  testDir: './tests', fullyParallel: false, workers: 1, timeout: 45000,
  expect: { timeout: 8000 }, reporter: [['list'], ['html', { open: 'never' }]],
  use: { baseURL: 'http://127.0.0.1:5173', viewport: { width: 1440, height: 1000 }, locale: 'ko-KR', timezoneId: 'Asia/Seoul', launchOptions: { executablePath: '/usr/bin/chromium', args: ['--no-sandbox'] }, trace: 'retain-on-failure', screenshot: 'only-on-failure' },
  webServer: [
    { command: 'DEMO_MODE=1 COMMUNITY_DB=.harness/browser-tests.sqlite3 .venv/bin/uvicorn community.app:app --host 127.0.0.1 --port 8000', cwd: '..', url: 'http://127.0.0.1:8000/api/health', reuseExistingServer: true },
    { command: 'npm run dev', url: 'http://127.0.0.1:5173', reuseExistingServer: true }
  ]
})
