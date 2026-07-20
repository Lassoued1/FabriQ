import { defineConfig, devices } from '@playwright/test'

const PORT = process.env.E2E_PORT ?? '5173'

// Projet SSO optionnel (E2E_SSO=1) : un second dev server Vite (5174) pointe
// sur un backend dédié (8001) configuré avec FABRIQ_OIDC_* vers le stub OIDC
// (backend/scripts/oidc_stub.py). La CI démarre stub + backend avant Playwright.
const SSO_ENABLED = process.env.E2E_SSO === '1'
const SSO_PORT = process.env.E2E_SSO_PORT ?? '5174'
const SSO_API = process.env.E2E_SSO_API ?? 'http://127.0.0.1:8001'

export default defineConfig({
  testDir: './e2e',
  timeout: 30_000,
  retries: 1,
  workers: 1,
  reporter: [['list'], ['html', { open: 'never' }]],

  use: {
    baseURL: `http://localhost:${PORT}`,
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },

  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
      testIgnore: /sso\.spec\.ts/,
    },
    ...(SSO_ENABLED
      ? [
          {
            name: 'sso',
            use: {
              ...devices['Desktop Chrome'],
              baseURL: `http://localhost:${SSO_PORT}`,
            },
            testMatch: /sso\.spec\.ts/,
          },
        ]
      : []),
  ],

  webServer: [
    {
      command: `npm run dev -- --port ${PORT} --strictPort`,
      url: `http://localhost:${PORT}`,
      reuseExistingServer: !process.env.CI,
      timeout: 30_000,
    },
    ...(SSO_ENABLED
      ? [
          {
            command: `npm run dev -- --port ${SSO_PORT} --strictPort`,
            url: `http://localhost:${SSO_PORT}`,
            reuseExistingServer: !process.env.CI,
            timeout: 30_000,
            env: { VITE_API_URL: SSO_API },
          },
        ]
      : []),
  ],
})
