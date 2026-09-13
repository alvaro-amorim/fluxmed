interface PlaceholderPageProps {
  title: string
  description: string
  phase: string
}

export function PlaceholderPage({ title, description, phase }: PlaceholderPageProps) {
  return (
    <main className="content-page">
      <div className="page-heading">
        <div>
          <p className="eyebrow eyebrow--dark">Centro de operações</p>
          <h1>{title}</h1>
          <p>{description}</p>
        </div>
        <span className="phase-badge">{phase}</span>
      </div>

      <section className="placeholder-panel">
        <div className="placeholder-grid" aria-hidden="true">
          <span />
          <span />
          <span />
          <span />
        </div>
        <div>
          <strong>Módulo em desenvolvimento</strong>
          <p>
            A navegação e a autenticação já são reais. Os dados operacionais desta área serão
            implementados na fase correspondente, sem mocks de negócio permanentes.
          </p>
        </div>
      </section>
    </main>
  )
}
