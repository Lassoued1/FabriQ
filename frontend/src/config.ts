export const API_BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'
export const APP_VERSION = 'v0.11.0'

export const fallbackExamples = [
  'Quels produits ont vu leur marge baisser le trimestre dernier ?',
  'Quels fournisseurs ont ete le plus souvent en retard ?',
  "Montre le chiffre d'affaires mensuel par categorie.",
  'Quels SKU risquent une rupture dans les 30 prochains jours ?',
]

// ─── i18n du panneau Question (partie gauche) ──────────────────────────────────
// Le backend comprend les questions en francais et en anglais ; ce selecteur
// bascule les libelles et les exemples affiches. Il ne traduit pas la reponse,
// qui reste dans la langue de la question posee.
export type QueryLang = 'fr' | 'en'

export const queryPanelStrings: Record<QueryLang, {
  heading: string
  ariaLabel: string
  placeholder: string
  analyze: string
  analyzing: string
  examplesTitle: string
}> = {
  fr: {
    heading: 'Question',
    ariaLabel: 'Question en langage naturel',
    placeholder: 'Posez une question metier en francais…',
    analyze: 'Analyser',
    analyzing: 'Analyse…',
    examplesTitle: 'Exemples',
  },
  en: {
    heading: 'Question',
    ariaLabel: 'Natural-language question',
    placeholder: 'Ask a business question in English…',
    analyze: 'Analyze',
    analyzing: 'Analyzing…',
    examplesTitle: 'Examples',
  },
}

// Exemples verifies (un par intention) — issus des suites d'evaluation,
// garantis de router correctement.
export const examplesByLang: Record<QueryLang, string[]> = {
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
