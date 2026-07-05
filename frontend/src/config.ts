export const API_BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'
export const APP_VERSION = 'v0.10.0'

export const fallbackExamples = [
  'Quels produits ont vu leur marge baisser le trimestre dernier ?',
  'Quels fournisseurs ont ete le plus souvent en retard ?',
  "Montre le chiffre d'affaires mensuel par categorie.",
  'Quels SKU risquent une rupture dans les 14 prochains jours ?',
]
