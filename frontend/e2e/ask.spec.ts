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

test.describe('Analysis (ask)', () => {
  test('example questions are displayed', async ({ page }) => {
    await login(page)
    // At least one example question should be visible on load
    const examples = page.locator('.examples-list button')
    await expect(examples.first()).toBeVisible({ timeout: 5_000 })
  })

  test('submit a question and receive a response', async ({ page }) => {
    await login(page)
    const input = page.getByLabel(/question en langage naturel/i)
    await input.fill('Quels fournisseurs ont ete le plus souvent en retard ?')
    await page.getByRole('button', { name: /analyser/i }).click()
    // The SQL panel of the response should appear
    await expect(page.locator('.sql-block pre')).toBeVisible({ timeout: 20_000 })
  })

  test('clicking an example runs the analysis', async ({ page }) => {
    await login(page)
    const firstExample = page.locator('.examples-list button').first()
    await firstExample.click()
    // Clicking an example triggers the analysis directly
    await expect(page.locator('.analysis-grid')).toBeVisible({ timeout: 20_000 })
  })
})
