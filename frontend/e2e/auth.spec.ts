import { test, expect } from '@playwright/test'

const ADMIN_EMAIL = 'admin@fabriq.io'
const ADMIN_PASSWORD = 'fabriq2024'

test.describe('Authentication', () => {
  test('shows login form when not authenticated', async ({ page }) => {
    await page.goto('/')
    await expect(page.getByRole('heading', { name: /fabriq/i })).toBeVisible()
    await expect(page.getByLabel(/email/i)).toBeVisible()
    await expect(page.getByLabel(/mot de passe/i)).toBeVisible()
    await expect(page.getByRole('button', { name: /connexion/i })).toBeVisible()
  })

  test('shows error on bad credentials', async ({ page }) => {
    await page.goto('/')
    await page.getByLabel(/email/i).fill('wrong@example.com')
    await page.getByLabel(/mot de passe/i).fill('badpassword')
    await page.getByRole('button', { name: /connexion/i }).click()
    await expect(page.getByText(/identifiants incorrects|unauthorized|401/i)).toBeVisible({ timeout: 5_000 })
  })

  test('logs in with valid credentials and shows main app', async ({ page }) => {
    await page.goto('/')
    await page.getByLabel(/email/i).fill(ADMIN_EMAIL)
    await page.getByLabel(/mot de passe/i).fill(ADMIN_PASSWORD)
    await page.getByRole('button', { name: /connexion/i }).click()
    // After login, the ask input should be visible
    await expect(page.getByPlaceholder(/question|analyse/i)).toBeVisible({ timeout: 10_000 })
  })

  test('logs out and returns to login form', async ({ page }) => {
    await page.goto('/')
    await page.getByLabel(/email/i).fill(ADMIN_EMAIL)
    await page.getByLabel(/mot de passe/i).fill(ADMIN_PASSWORD)
    await page.getByRole('button', { name: /connexion/i }).click()
    await page.getByRole('button', { name: /déconnexion|logout/i }).click()
    await expect(page.getByLabel(/email/i)).toBeVisible({ timeout: 5_000 })
  })
})
