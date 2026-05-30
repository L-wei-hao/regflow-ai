import './App.css'

const pillars = [
  {
    title: 'Grounded AI recommendations',
    description:
      'Policy-aware recommendations with retrieval context, citations, and explainability designed for regulated workflows.',
  },
  {
    title: 'Human approval gates',
    description:
      'Sensitive decisions stay reviewable with explicit approver handoff, comments, and final decision tracking.',
  },
  {
    title: 'Operational auditability',
    description:
      'Every action is meant to be traceable across cases, workflow runs, model outputs, and reviewer interventions.',
  },
]

const milestones = [
  'Foundation scaffold across web, API, and AI orchestration services',
  'PostgreSQL + pgvector persistence for cases, workflows, and retrieval',
  'Case intake, policy retrieval, recommendation generation, and approval queue',
  'Production deployment with HTTPS, screenshots, and demo-ready seeded data',
]

function App() {
  return (
    <main className="page-shell">
      <section className="hero-section">
        <div className="eyebrow">Flagship portfolio build in progress</div>
        <h1>RegFlow AI</h1>
        <p className="hero-copy">
          An AI workflow automation platform for regulated operations — combining
          retrieval-augmented intelligence, human approval gates, and audit-ready
          operational controls.
        </p>

        <div className="hero-actions">
          <a className="primary-action" href="https://github.com" target="_blank" rel="noreferrer">
            GitHub portfolio project
          </a>
          <span className="status-pill">Scaffold complete • MVP execution started</span>
        </div>
      </section>

      <section className="section-grid" aria-label="Platform pillars">
        {pillars.map((pillar) => (
          <article key={pillar.title} className="info-card">
            <h2>{pillar.title}</h2>
            <p>{pillar.description}</p>
          </article>
        ))}
      </section>

      <section className="two-column-layout">
        <article className="panel">
          <div className="panel-label">Target use case</div>
          <h2>Compliance-heavy case review</h2>
          <p>
            Upload policy documents, enrich cases with retrieval context, generate an AI
            recommendation, and route the final decision through a human approver with
            a persistent audit trail.
          </p>
          <ul>
            <li>Customer onboarding / KYC review</li>
            <li>Internal operations approvals</li>
            <li>Policy-guided exception handling</li>
          </ul>
        </article>

        <article className="panel">
          <div className="panel-label">Execution roadmap</div>
          <h2>Current milestones</h2>
          <ol>
            {milestones.map((milestone) => (
              <li key={milestone}>{milestone}</li>
            ))}
          </ol>
        </article>
      </section>
    </main>
  )
}

export default App
