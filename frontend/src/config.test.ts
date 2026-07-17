import { describe, expect, it } from 'vitest'
import { examplesByLang, queryPanelStrings } from './config'

describe('i18n du panneau Question', () => {
  it('expose les libelles pour le francais et l anglais', () => {
    for (const lang of ['fr', 'en'] as const) {
      const s = queryPanelStrings[lang]
      expect(s.heading).toBeTruthy()
      expect(s.analyze).toBeTruthy()
      expect(s.placeholder).toBeTruthy()
      expect(s.examplesTitle).toBeTruthy()
    }
  })

  it('propose des exemples dans les deux langues', () => {
    expect(examplesByLang.fr.length).toBeGreaterThan(0)
    expect(examplesByLang.en.length).toBe(10)
  })

  it('les exemples anglais sont bien en anglais (pas de residu francais)', () => {
    for (const q of examplesByLang.en) {
      expect(q).not.toMatch(/quels?|montre|fournisseurs/i)
    }
  })
})
