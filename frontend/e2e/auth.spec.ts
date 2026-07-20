import { test, expect } from '@playwright/test'

const ADMIN_EMAIL = 'admin@fabriq.io'
const ADMIN_PASSWORD = 'fabriq2024'

test.describe('Authentication', () => {
  test('shows login form when not authenticated', async ({ page }) => {
    await page.goto('/')
    await expect(page.getByRole('heading', { name: /fabriq/i })).toBeVisible()
    await expect(page.getByLabel(/email/i)).toBeVisible()
    await expect(page.getByLabel(/mot de passe/i)).toBeVisible()
    await expect(page.getByRole('button', { name: 'Se connecter', exact: true })).toBeVisible()
  })

  test('shows error on bad credentials', async ({ page }) => {
    await page.goto('/')
    await page.getByLabel(/email/i).fill('wrong@example.com')
    await page.getByLabel(/mot de passe/i).fill('badpassword')
    await page.getByRole('button', { name: 'Se connecter', exact: true }).click()
    await expect(page.getByText(/email ou mot de passe incorrect/i)).toBeVisible({ timeout: 5_000 })
  })

  test('logs in with valid credentials and shows main app', async ({ page }) => {
    await page.goto('/')
    await page.getByLabel(/email/i).fill(ADMIN_EMAIL)
    await page.getByLabel(/mot de passe/i).fill(ADMIN_PASSWORD)
    await page.getByRole('button', { name: 'Se connecter', exact: true }).click()
    // After login, the question textarea should be visible
    await expect(page.getByLabel(/question en langage naturel/i)).toBeVisible({ timeout: 10_000 })
  })

  test('logs out and returns to login form', async ({ page }) => {
    await page.goto('/')
    await page.getByLabel(/email/i).fill(ADMIN_EMAIL)
    await page.getByLabel(/mot de passe/i).fill(ADMIN_PASSWORD)
    await page.getByRole('button', { name: 'Se connecter', exact: true }).click()
    await expect(page.getByLabel(/question en langage naturel/i)).toBeVisible({ timeout: 10_000 })
    await page.getByRole('button', { name: /se déconnecter/i }).click()
    await expect(page.getByLabel(/email/i)).toBeVisible({ timeout: 5_000 })
  })
})
