// Enregistre le scenario de demo FabriQ en frames PNG pour docs/assets.
//
// Scenario v0.15.0 : page de login trilingue (FR -> EN -> DE), connexion en
// allemand, la langue choisie se propage a l'application, question en
// allemand, retour en francais via le selecteur de l'app, question en
// francais avec parcours du resultat (graphique, tableau, SQL).
//
// Prerequis :
//   - backend sur http://127.0.0.1:8000 (utilisateur admin@fabriq.io / fabriq2024)
//   - frontend Vite (DEMO_URL, defaut http://localhost:5173)
// Usage :
//   node scripts/record-demo.mjs [dossier-frames]
// Puis assembler le GIF (voir scripts/make_gif.py a la racine du repo).

import { chromium } from '@playwright/test'
import { mkdirSync, writeFileSync } from 'node:fs'
import { join } from 'node:path'

const BASE_URL = process.env.DEMO_URL ?? 'http://localhost:5173'
const framesDir = process.argv[2] ?? 'demo-frames'
mkdirSync(framesDir, { recursive: true })

const manifest = []
let index = 0

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1280, height: 800 } })

async function snap(durationMs) {
  const name = `frame_${String(index).padStart(3, '0')}.png`
  await page.screenshot({ path: join(framesDir, name) })
  manifest.push({ name, duration: durationMs })
  index += 1
}

// Selecteurs independants de la langue : les libelles changent avec le
// selecteur FR/EN/DE, on cible donc les classes et types plutot que les textes.
const loginLangButton = (code) =>
  page.locator('.login-card .lang-toggle button', { hasText: code })
const appLangButton = (code) =>
  page.locator('.query-panel .lang-toggle button', { hasText: code })
const question = page.locator('.question-form textarea')
const analyzeButton = page.locator('.question-form button[type="submit"]')

async function typeProgressively(text, chunks = 4) {
  for (let i = 1; i <= chunks; i += 1) {
    await question.fill(text.slice(0, Math.ceil((text.length * i) / chunks)))
    await snap(i === chunks ? 700 : 380)
  }
}

// 1. Page de connexion en francais (langue par defaut)
await page.goto(BASE_URL)
await page.locator('.login-form button[type="submit"]').waitFor()
await snap(1300)

// 2. Nouveaute v0.15.0 : selecteur de langue sur la page de login
await loginLangButton('EN').click()
await snap(1000)
await loginLangButton('DE').click()
await snap(1200)

// 3. Connexion (libelles en allemand)
await page.locator('.login-form input[type="email"]').fill('admin@fabriq.io')
await snap(600)
await page.locator('.login-form input[type="password"]').fill('fabriq2024')
await snap(700)
await page.locator('.login-form button[type="submit"]').click()

// 4. La langue choisie au login se propage : l'application arrive en allemand.
// L'app lance automatiquement une premiere question au montage : on attend
// la fin de cette analyse pour une frame stable et un tableau de bord peuple.
await question.waitFor({ timeout: 10_000 })
await page.locator('.analysis-grid').waitFor({ timeout: 20_000 })
await page.waitForTimeout(600)
await snap(1600)

// Attend que le SQL affiche change par rapport a `before` (l'auto-analyse du
// montage remplit deja .sql-block, un simple waitFor ne suffit pas).
async function waitForNewSql(before) {
  await page.waitForFunction(
    (prev) => {
      const sql = document.querySelector('.sql-block pre')?.textContent
      return Boolean(sql) && sql !== prev
    },
    before,
    { timeout: 20_000 },
  )
}

// 5. Question en allemand (intention differente de l'auto-analyse ; le
// parametre "30 Tagen" est extrait de la question et binde dans le SQL)
const german = 'Welche Artikel haben in den nächsten 30 Tagen einen Engpass?'
let previousSql = await page.locator('.sql-block pre').textContent()
await typeProgressively(german)
await analyzeButton.click()
await waitForNewSql(previousSql)
await page.waitForTimeout(600)
await snap(1700)
await page.locator('.chart-block').scrollIntoViewIfNeeded()
await page.waitForTimeout(400)
await snap(1800)

// 6. Retour en francais via le selecteur de l'application
await page.evaluate(() => window.scrollTo(0, 0))
await appLangButton('FR').click()
await page.waitForTimeout(300)
await snap(1300)

// 7. Question en francais et parcours du resultat
previousSql = await page.locator('.sql-block pre').textContent()
await typeProgressively('Quels produits ont vu leur marge baisser le trimestre dernier ?')
await analyzeButton.click()
await waitForNewSql(previousSql)
await page.waitForTimeout(700)
await snap(1700)

// 8. Graphique, tableau, SQL
await page.locator('.chart-block').scrollIntoViewIfNeeded()
await page.waitForTimeout(400)
await snap(1700)
await page.locator('.table-block').scrollIntoViewIfNeeded()
await page.waitForTimeout(300)
await snap(1400)
await page.locator('.sql-block').scrollIntoViewIfNeeded()
await page.waitForTimeout(300)
await snap(2000)

writeFileSync(join(framesDir, 'manifest.json'), JSON.stringify(manifest, null, 2))
await browser.close()
console.log(`${index} frames -> ${framesDir}/`)
