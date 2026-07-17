import { describe, expect, it } from 'vitest'
import { examplesByLang } from './config'
import { translations } from './i18n'

describe('i18n', () => {
  it('couvre le francais et l anglais avec la meme forme', () => {
    const keys = (o: object): string[] =>
      Object.entries(o).flatMap(([k, v]) =>
        v && typeof v === 'object' ? Object.keys(v).map((sub) => `${k}.${sub}`) : [k],
      )
    expect(keys(translations.en)).toEqual(keys(translations.fr))
  })

  it('traduit reellement (les libelles anglais different du francais)', () => {
    expect(translations.en.result.answer).not.toBe(translations.fr.result.answer)
    expect(translations.en.obs.heading).not.toBe(translations.fr.obs.heading)
    expect(translations.en.alerts.create).toBe('Create')
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
