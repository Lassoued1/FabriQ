export const API_BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'
export const APP_VERSION = 'v0.13.0'

export const fallbackExamples = [
  'Quels produits ont vu leur marge baisser le trimestre dernier ?',
  'Quels fournisseurs ont ete le plus souvent en retard ?',
  "Montre le chiffre d'affaires mensuel par categorie.",
  'Quels SKU risquent une rupture dans les 30 prochains jours ?',
]

// ─── Exemples de questions par langue ──────────────────────────────────────────
// Le backend comprend les questions en francais et en anglais ; le selecteur de
// langue (voir i18n.tsx) bascule les libelles ET les exemples affiches. La
// reponse, elle, reste dans la langue de la question posee.
// Exemples verifies (un par intention) — issus des suites d'evaluation,
// garantis de router correctement.
export const examplesByLang: Record<'fr' | 'en', string[]> = {
  fr: fallbackExamples,
  en: [
    'Which products saw their margin drop last quarter?',
    'Which items are at risk of a stockout in the next 30 days?',
    'Which suppliers were most often late?',
    'Which production lines had the most defects?',
    'Show the monthly revenue by category.',
    'Which products have been sitting in stock too long?',
    'Which routes have become more expensive?',
    'Which products have the highest return rate?',
    'Which customers account for the largest share of revenue?',
    'What changed unusually last month?',
  ],
}
