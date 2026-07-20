import { describe, expect, it } from 'vitest'
import { examplesByLang } from './config'
import { translations } from './i18n'

const keys = (o: object): string[] =>
  Object.entries(o).flatMap(([k, v]) =>
    v && typeof v === 'object' ? Object.keys(v).map((sub) => `${k}.${sub}`) : [k],
  )

describe('i18n', () => {
  it('couvre le francais, l anglais et l allemand avec la meme forme', () => {
    expect(keys(translations.en)).toEqual(keys(translations.fr))
    expect(keys(translations.de)).toEqual(keys(translations.fr))
  })

  it('traduit reellement (les libelles anglais different du francais)', () => {
    expect(translations.en.result.answer).not.toBe(translations.fr.result.answer)
    expect(translations.en.obs.heading).not.toBe(translations.fr.obs.heading)
    expect(translations.en.alerts.create).toBe('Create')
  })

  it('traduit reellement en allemand', () => {
    expect(translations.de.result.answer).not.toBe(translations.fr.result.answer)
    expect(translations.de.query.analyze).toBe('Analysieren')
    expect(translations.de.alerts.create).toBe('Erstellen')
  })

  it('propose des exemples dans les trois langues', () => {
    expect(examplesByLang.fr.length).toBeGreaterThan(0)
    expect(examplesByLang.en.length).toBe(13)
    expect(examplesByLang.de.length).toBe(13)
  })

  it('les exemples anglais sont bien en anglais (pas de residu francais)', () => {
    for (const q of examplesByLang.en) {
      expect(q).not.toMatch(/quels?|montre|fournisseurs/i)
    }
  })

  it('les exemples allemands sont bien en allemand (pas de residu FR/EN)', () => {
    for (const q of examplesByLang.de) {
      expect(q).not.toMatch(/quels?|montre|which|show the/i)
      expect(q).toMatch(/welche|zeige|was|wie/i)
    }
  })
})
