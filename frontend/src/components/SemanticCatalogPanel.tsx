import { Layers3 } from 'lucide-react'
import type { CatalogResponse, CatalogTab } from '../types'
import { useLang } from '../i18n'

export function SemanticCatalogPanel({
  catalog,
  activeTab,
  error,
  onSelectTab,
  onAsk,
}: {
  catalog: CatalogResponse | null
  activeTab: CatalogTab
  error: string | null
  onSelectTab: (tab: CatalogTab) => void
  onAsk: (question: string) => void
}) {
  const { t } = useLang()
  return (
    <section className="catalog-panel">
      <div className="panel-heading compact">
        <Layers3 size={18} />
        <h2>{t.catalog.heading}</h2>
      </div>

      <div className="catalog-tabs" role="tablist" aria-label={t.catalog.aria}>
        <button
          type="button"
          className={activeTab === 'intents' ? 'active' : undefined}
          onClick={() => onSelectTab('intents')}
        >
          {t.catalog.intents}
        </button>
        <button
          type="button"
          className={activeTab === 'tables' ? 'active' : undefined}
          onClick={() => onSelectTab('tables')}
        >
          {t.catalog.tables}
        </button>
      </div>

      {error && <div className="ops-error">{error}</div>}
      {!catalog && !error && <div className="catalog-empty">{t.catalog.loading}</div>}

      {catalog && activeTab === 'intents' && (
        <div className="catalog-list">
          {catalog.intents.map((intent) => (
            <article key={intent.id} className="catalog-item">
              <div className="catalog-item-title">
                <strong>{intent.label}</strong>
                <span>{intent.chart.type}</span>
              </div>
              <p>{intent.description}</p>
              <div className="keyword-row">
                {intent.keywords.slice(0, 5).map((keyword) => (
                  <span key={keyword}>{keyword}</span>
                ))}
              </div>
              <button type="button" onClick={() => onAsk(intent.example_question)}>
                {intent.example_question}
              </button>
            </article>
          ))}
        </div>
      )}

      {catalog && activeTab === 'tables' && (
        <div className="catalog-list">
          {catalog.tables.map((table) => (
            <article key={table.name} className="catalog-item">
              <div className="catalog-item-title">
                <strong>{table.label}</strong>
                <span>{table.columns.length} {t.catalog.columns}</span>
              </div>
              <p>{table.description}</p>
              <div className="column-list">
                {table.columns.slice(0, 6).map((column) => (
                  <span key={column.name} title={column.description}>
                    {column.name}
                  </span>
                ))}
              </div>
            </article>
          ))}
        </div>
      )}
    </section>
  )
}
