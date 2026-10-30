import { defineConfig } from '@playwright/test'
export default defineConfig({
  testDir: './demo-tests', outputDir: './demo-test-results', workers: 1, timeout: 45000, expect: { timeout: 10000 }, reporter: 'list',
  use: { baseURL: process.env.DEMO_TEST_ORIGIN || 'http://127.0.0.1:4174', viewport: { width: 390, height: 844 }, locale: 'ko-KR', timezoneId: 'Asia/Seoul', launchOptions: { executablePath: '/usr/bin/chromium', args: ['--no-sandbox'] }, trace: 'retain-on-failure', screenshot: 'only-on-failure' },
  webServer: process.env.DEMO_TEST_ORIGIN ? undefined : { command: 'npm run preview:demo', url: 'http://127.0.0.1:4174', reuseExistingServer: false },
})
