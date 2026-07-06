// Enregistre le scenario de demo FabriQ en frames PNG pour docs/assets.
//
// Prerequis :
//   - backend sur http://127.0.0.1:8000 (utilisateur admin@fabriq.io / fabriq2024)
//   - frontend Vite sur http://localhost:5199 (VITE_API_URL pointant sur le backend)
// Usage :
//   node scripts/record-demo.mjs [dossier-frames]
// Puis assembler le GIF (voir scripts/make_gif.py a la racine du repo).

import { chromium } from '@playwright/test'
import { mkdirSync, writeFileSync } from 'node:fs'
import { join } from 'node:path'

const BASE_URL = process.env.DEMO_URL ?? 'http://localhost:5199'
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

// 1. Page de connexion
await page.goto(BASE_URL)
await page.getByRole('button', { name: /se connecter/i }).waitFor()
await snap(1100)

await page.getByLabel(/email/i).fill('admin@fabriq.io')
await snap(600)
await page.getByLabel(/mot de passe/i).fill('fabriq2024')
await snap(700)

// 2. Connexion -> application principale
await page.getByRole('button', { name: /se connecter/i }).click()
const question = page.getByLabel(/question en langage naturel/i)
await question.waitFor({ timeout: 10_000 })
await page.waitForTimeout(600)
await snap(1300)

// 3. Saisie progressive de la question
const text = 'Quels produits ont vu leur marge baisser le trimestre dernier ?'
const chunks = 4
for (let i = 1; i <= chunks; i += 1) {
  await question.fill(text.slice(0, Math.ceil((text.length * i) / chunks)))
  await snap(i === chunks ? 700 : 380)
}

// 4. Analyse
await page.getByRole('button', { name: /analyser/i }).click()
await snap(500)
await page.locator('.analysis-grid').waitFor({ timeout: 20_000 })
await page.waitForTimeout(700)
await snap(1700)

// 5. Parcours du resultat : graphique, tableau, SQL
await page.locator('.chart-block').scrollIntoViewIfNeeded()
await page.waitForTimeout(400)
await snap(1700)
await page.locator('.table-block').scrollIntoViewIfNeeded()
await page.waitForTimeout(300)
await snap(1400)
await page.locator('.sql-block').scrollIntoViewIfNeeded()
await page.waitForTimeout(300)
await snap(1900)

// 6. Meme boucle en allemand : routage bilingue
await page.evaluate(() => window.scrollTo(0, 0))
const german = 'Welche Lieferanten waren am häufigsten verspätet?'
for (let i = 1; i <= chunks; i += 1) {
  await question.fill(german.slice(0, Math.ceil((german.length * i) / chunks)))
  await snap(i === chunks ? 700 : 380)
}
await page.getByRole('button', { name: /analyser/i }).click()
await page.waitForFunction(
  () => document.querySelector('.sql-block pre')?.textContent?.includes('supplier_delays'),
  { timeout: 20_000 },
)
await page.waitForTimeout(600)
await snap(1700)
await page.locator('.chart-block').scrollIntoViewIfNeeded()
await page.waitForTimeout(400)
await snap(2000)

writeFileSync(join(framesDir, 'manifest.json'), JSON.stringify(manifest, null, 2))
await browser.close()
console.log(`${index} frames -> ${framesDir}/`)
