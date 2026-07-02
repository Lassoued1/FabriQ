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

test.describe('Analysis (ask)', () => {
  test('example questions are displayed', async ({ page }) => {
    await login(page)
    // At least one example question should be visible on load
    const examples = page.locator('button[class*="example"]')
    await expect(examples.first()).toBeVisible({ timeout: 5_000 })
  })

  test('submit a question and receive a response', async ({ page }) => {
    await login(page)
    const input = page.getByPlaceholder(/question|analyse/i)
    await input.fill('Quelle est la tendance de marge ?')
    await page.getByRole('button', { name: /analyser|envoyer/i }).click()
    // Result table or chart should appear
    await expect(page.locator('[class*="result"], table, [class*="chart"]').first()).toBeVisible({ timeout: 20_000 })
  })

  test('clicking an example populates the input', async ({ page }) => {
    await login(page)
    const firstExample = page.locator('button[class*="example"]').first()
    const exampleText = await firstExample.textContent()
    await firstExample.click()
    const input = page.getByPlaceholder(/question|analyse/i)
    await expect(input).toHaveValue(exampleText?.trim() ?? '')
  })
})
