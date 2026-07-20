import { test, expect } from '@playwright/test'

// Parcours SSO complet contre le stub OIDC (backend/scripts/oidc_stub.py).
// Ne tourne que dans le projet "sso" (E2E_SSO=1) : un backend dédié avec
// FABRIQ_OIDC_* pointe sur le stub, un second dev server Vite pointe sur ce
// backend. Voir playwright.config.ts et le job e2e de la CI.

test.describe('SSO (OIDC)', () => {
  test('the SSO button is shown when the backend has OIDC enabled', async ({ page }) => {
    await page.goto('/')
    await expect(page.getByRole('button', { name: 'Se connecter avec SSO' })).toBeVisible()
    // Le login local reste disponible à côté.
    await expect(page.getByRole('button', { name: 'Se connecter', exact: true })).toBeVisible()
  })

  test('full SSO journey: provider login lands back in the app', async ({ page }) => {
    await page.goto('/')
    await page.getByRole('button', { name: 'Se connecter avec SSO' }).click()

    // Page de login factice du stub — le state et le PKCE sont déjà passés
    // dans l'URL d'autorisation générée par le backend.
    await expect(page.getByRole('heading', { name: /fournisseur sso/i })).toBeVisible({
      timeout: 10_000,
    })
    await page.getByRole('link', { name: /continuer/i }).click()

    // Callback backend -> échange du code (PKCE vérifié par le stub) ->
    // validation de l'id_token -> JWT FabriQ -> retour frontend en #sso_token.
    await expect(page.getByLabel(/question en langage naturel/i)).toBeVisible({
      timeout: 15_000,
    })
    // Le fragment a été consommé et nettoyé de l'URL.
    expect(new URL(page.url()).hash).toBe('')
    // L'identité vient bien du SSO : un compte absent de FABRIQ_USERS.
    const apiBase = process.env.E2E_SSO_API ?? 'http://127.0.0.1:8001'
    const me = await page.evaluate(async (base) => {
      const token = localStorage.getItem('fabriq_token')
      const res = await fetch(`${base}/api/auth/me`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      return res.json()
    }, apiBase)
    expect(me.email).toBe('sso.demo@fabriq.io')
    expect(me.tenant_id).toBe('tenant_demo')
  })
})
