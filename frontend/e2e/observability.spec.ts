import { test, expect, Page } from '@playwright/test'

const ADMIN_EMAIL = 'admin@fabriq.io'
const ADMIN_PASSWORD = 'fabriq2024'

async function login(page: Page) {
  await page.goto('/')
  await page.getByLabel(/email/i).fill(ADMIN_EMAIL)
  await page.getByLabel(/mot de passe/i).fill(ADMIN_PASSWORD)
  await page.getByRole('button', { name: 'Se connecter', exact: true }).click()
  await page.getByLabel(/question en langage naturel/i).waitFor({ timeout: 10_000 })
}

test.describe('Observability panel', () => {
  test('health status is visible in header', async ({ page }) => {
    await login(page)
    // Health badges (API ok, database, read-only) live in the status strip
    const strip = page.locator('.status-strip')
    await expect(strip).toBeVisible()
    await expect(strip.getByText(/api/i)).toBeVisible()
    await expect(strip.getByText(/read-only/i)).toBeVisible()
  })

  test('observability panel shows audit trail section', async ({ page }) => {
    await login(page)
    const panel = page.locator('.observability-panel')
    await expect(panel).toBeVisible()
    await expect(panel.getByRole('heading', { name: /observabilite/i })).toBeVisible()
    // CSV and XLSX exports are available
    await expect(panel.getByRole('button', { name: /csv/i })).toBeVisible()
    await expect(panel.getByRole('button', { name: /xlsx/i })).toBeVisible()
  })

  test('alerts panel is accessible to admin', async ({ page }) => {
    await login(page)
    const panel = page.locator('.alerts-panel')
    await expect(panel).toBeVisible()
    await expect(panel.getByRole('heading', { name: /alertes/i })).toBeVisible()
    // The "new alert" button opens the creation form
    await panel.getByRole('button', { name: /nouvelle alerte/i }).click()
    await expect(panel.getByPlaceholder(/nom de l'alerte/i)).toBeVisible({ timeout: 5_000 })
  })
})
