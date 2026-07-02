import { test, expect, Page } from '@playwright/test'

const ADMIN_EMAIL = 'admin@fabriq.io'
const ADMIN_PASSWORD = 'fabriq2024'

async function login(page: Page) {
  await page.goto('/')
  await page.getByLabel(/email/i).fill(ADMIN_EMAIL)
  await page.getByLabel(/mot de passe/i).fill(ADMIN_PASSWORD)
  await page.getByRole('button', { name: /connexion/i }).click()
  await page.getByPlaceholder(/question|analyse/i).waitFor({ timeout: 10_000 })
}

test.describe('Observability panel', () => {
  test('health status is visible in header', async ({ page }) => {
    await login(page)
    // Health badge (API ok / LLM) should be somewhere in the header
    await expect(page.locator('[class*="health"], [class*="status"]').first()).toBeVisible()
  })

  test('audit tab shows events list or empty state', async ({ page }) => {
    await login(page)
    await page.getByRole('tab', { name: /audit|journal/i }).click()
    // Either event rows or "aucun événement" message
    await expect(
      page.locator('[class*="audit"], table, [class*="empty"]').first()
    ).toBeVisible({ timeout: 5_000 })
  })

  test('alerts tab is accessible to admin', async ({ page }) => {
    await login(page)
    await page.getByRole('tab', { name: /alert/i }).click()
    // Alert form or empty list should be visible
    await expect(page.locator('[class*="alert"], [class*="rule"], button').first()).toBeVisible({ timeout: 5_000 })
  })
})
