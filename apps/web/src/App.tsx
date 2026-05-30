/* eslint-disable react-hooks/set-state-in-effect */
import { useCallback, useEffect, useMemo, useState } from 'react'
import './App.css'

type MetricMap = Record<string, number>

type WorkflowStep = {
  step_id: string
  name: string
  step_type: string
}

type WorkflowCard = {
  workflow_id: string
  name: string
  version: string
  regulated: boolean
  step_count: number
  blocking_steps: string[]
  steps: WorkflowStep[]
}

type CaseCard = {
  case_id: string
  workflow_id: string
  applicant_name: string
  submitted_documents: string[]
  policy_tags: string[]
  status: string
  status_label: string
  ai_outcome: string | null
  ai_summary: string | null
  citations: Array<{ source: string; excerpt: string }>
  assigned_reviewer: string | null
  reviewer_comment: string | null
  document_count: number
  policy_tag_count: number
  citation_count: number
  latest_audit_event: AuditEvent | null
  risk_posture: string
}

type AuditEvent = {
  event_id: string
  entity_type: string
  entity_id: string
  action: string
  occurred_at: string
  actor: { id: string; type: string }
  details: Record<string, string>
  summary: string
}

type DashboardResponse = {
  product: string
  service: string
  headline: string
  metrics: {
    total_workflows: number
    total_cases: number
    pending_reviews: number
    approved_cases: number
    escalated_cases: number
  }
  status_breakdown: MetricMap
  workflows: WorkflowCard[]
  cases: CaseCard[]
  pending_approvals: CaseCard[]
  recent_audit_events: AuditEvent[]
  focus_case_id: string
  generated_at: string | null
}

type CaseDetailResponse = {
  case: CaseCard
  audit_timeline: AuditEvent[]
}

const capabilityBullets = [
  'Policy-aware case review with human approval gates',
  'Traceable AI recommendations with cited evidence',
  'Workflow templates that show regulated-domain thinking',
  'Recruiter-ready architecture, docs, and CI polish',
]

const steps = [
  'Register a workflow template with an approval gate',
  'Intake cases and start AI review',
  'Capture policy-backed recommendations',
  'Route sensitive decisions to a human reviewer',
]

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, '') ?? ''

function buildApiUrl(path: string) {
  return `${apiBaseUrl}${path}`
}

async function fetchJson<T>(path: string): Promise<T> {
  const response = await fetch(buildApiUrl(path), {
    headers: {
      Accept: 'application/json',
    },
  })

  if (!response.ok) {
    throw new Error(`Request failed (${response.status}) for ${path}`)
  }

  return response.json() as Promise<T>
}

function formatTimestamp(value: string | null | undefined) {
  if (!value) return '—'
  return new Intl.DateTimeFormat('en-SG', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value))
}

function formatLabel(value: string) {
  return value.replace(/_/g, ' ').replace(/\b\w/g, (char) => char.toUpperCase())
}

function toneForCase(status: string) {
  switch (status) {
    case 'approved':
      return 'success'
    case 'escalated':
      return 'warning'
    case 'awaiting_human_approval':
      return 'attention'
    case 'in_review':
      return 'info'
    default:
      return 'muted'
  }
}

function App() {
  const [dashboard, setDashboard] = useState<DashboardResponse | null>(null)
  const [selectedCaseId, setSelectedCaseId] = useState<string | null>(null)
  const [selectedCaseDetail, setSelectedCaseDetail] = useState<CaseDetailResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const selectedCaseFromDashboard = useMemo(() => {
    if (!dashboard || !selectedCaseId) return null
    return dashboard.cases.find((item) => item.case_id === selectedCaseId) ?? null
  }, [dashboard, selectedCaseId])

  const loadDashboard = useCallback(
    async (preserveSelection = false) => {
      try {
        setError(null)
        const data = await fetchJson<DashboardResponse>('/api/dashboard')
        setDashboard(data)

        const nextSelection =
          (preserveSelection ? selectedCaseId : null) ?? data.focus_case_id ?? data.cases[0]?.case_id ?? null

        if (nextSelection) {
          setSelectedCaseId(nextSelection)
        }
      } catch (loadError) {
        setError(loadError instanceof Error ? loadError.message : 'Failed to load dashboard')
      } finally {
        setLoading(false)
        setRefreshing(false)
      }
    },
    [selectedCaseId],
  )

  useEffect(() => {
    void loadDashboard()
  }, [loadDashboard])

  useEffect(() => {
    if (!selectedCaseId) {
      setSelectedCaseDetail(null)
      return
    }

    let cancelled = false

    async function loadCaseDetail() {
      try {
        const data = await fetchJson<CaseDetailResponse>(`/api/cases/${selectedCaseId}/audit`)
        if (!cancelled) {
          setSelectedCaseDetail(data)
        }
      } catch (loadError) {
        if (!cancelled) {
          setError(loadError instanceof Error ? loadError.message : 'Failed to load case detail')
        }
      }
    }

    void loadCaseDetail()

    return () => {
      cancelled = true
    }
  }, [selectedCaseId])

  const handleRefresh = () => {
    setRefreshing(true)
    void loadDashboard(true)
  }

  const selectedCase = selectedCaseDetail?.case ?? selectedCaseFromDashboard
  const auditEvents = selectedCaseDetail?.audit_timeline ?? []
  const isInitialLoading = loading && !dashboard

  if (isInitialLoading) {
    return (
      <main className="page-shell">
        <section className="hero-section">
          <div className="eyebrow">Bootstrapping live demo</div>
          <h1>RegFlow AI</h1>
          <p className="hero-copy">
            Preparing the control-plane dashboard, seeding workflows, and loading the audit-ready case queue.
          </p>
          <div className="hero-actions">
            <span className="status-pill">Loading demo dataset…</span>
          </div>
        </section>
      </main>
    )
  }

  return (
    <main className="page-shell">
      <section className="hero-section">
        <div className="hero-topline">
          <div>
            <div className="eyebrow">Live portfolio project</div>
            <h1>{dashboard?.product ?? 'RegFlow AI'}</h1>
          </div>
          <div className="hero-meta">
            <span className="status-pill">{dashboard?.service ?? 'control-plane'}</span>
            <button className="ghost-button" type="button" onClick={handleRefresh} disabled={refreshing}>
              {refreshing ? 'Refreshing…' : 'Refresh live data'}
            </button>
          </div>
        </div>

        <p className="hero-copy">{dashboard?.headline ?? 'AI workflow automation for regulated operations'}</p>

        <div className="hero-actions">
          <a className="primary-action" href="https://github.com/L-wei-hao/regflow-ai" target="_blank" rel="noreferrer">
            View the repository
          </a>
          <span className="status-pill">Updated {formatTimestamp(dashboard?.generated_at)}</span>
        </div>

        {error ? <div className="error-banner">{error}</div> : null}
      </section>

      <section className="metric-grid" aria-label="Key metrics">
        <MetricCard label="Workflows" value={dashboard?.metrics.total_workflows ?? '—'} tone="info" />
        <MetricCard label="Cases" value={dashboard?.metrics.total_cases ?? '—'} tone="default" />
        <MetricCard label="Pending reviews" value={dashboard?.metrics.pending_reviews ?? '—'} tone="attention" />
        <MetricCard label="Approved" value={dashboard?.metrics.approved_cases ?? '—'} tone="success" />
        <MetricCard label="Escalated" value={dashboard?.metrics.escalated_cases ?? '—'} tone="warning" />
      </section>

      <section className="two-column-layout">
        <article className="panel">
          <div className="panel-label">Why this project stands out</div>
          <h2>Recruiter-friendly signal</h2>
          <ul className="bullet-list">
            {capabilityBullets.map((bullet) => (
              <li key={bullet}>{bullet}</li>
            ))}
          </ul>
        </article>

        <article className="panel">
          <div className="panel-label">Execution story</div>
          <h2>What the platform demonstrates</h2>
          <ol className="numbered-list">
            {steps.map((step) => (
              <li key={step}>{step}</li>
            ))}
          </ol>
        </article>
      </section>

      <section className="content-grid">
        <article className="panel panel-span-2">
          <div className="panel-header">
            <div>
              <div className="panel-label">Live workflows</div>
              <h2>Template library</h2>
            </div>
            <span className="mini-pill">{dashboard?.workflows.length ?? 0} active templates</span>
          </div>

          <div className="workflow-grid">
            {dashboard?.workflows.map((workflow) => (
              <article key={workflow.workflow_id} className="workflow-card">
                <div className="workflow-card__topline">
                  <strong>{workflow.name}</strong>
                  <span>{workflow.version}</span>
                </div>
                <div className="workflow-card__meta">
                  <span className="mini-pill">{workflow.regulated ? 'regulated' : 'unregulated'}</span>
                  <span className="mini-pill">{workflow.step_count} steps</span>
                  <span className="mini-pill">{workflow.blocking_steps.length} approval gates</span>
                </div>
                <div className="step-list">
                  {workflow.steps.map((step) => (
                    <span key={step.step_id} className="step-chip">
                      {formatLabel(step.step_type)}
                    </span>
                  ))}
                </div>
              </article>
            ))}
          </div>
        </article>

        <article className="panel">
          <div className="panel-label">Case queue</div>
          <h2>Operational worklist</h2>
          <div className="case-list">
            {dashboard?.cases.map((item) => (
              <button
                key={item.case_id}
                type="button"
                className={`case-card case-card--${toneForCase(item.status)} ${item.case_id === selectedCaseId ? 'case-card--selected' : ''}`}
                onClick={() => setSelectedCaseId(item.case_id)}
              >
                <div className="case-card__row">
                  <strong>{item.case_id}</strong>
                  <span className="status-badge">{item.status_label}</span>
                </div>
                <p>{item.applicant_name}</p>
                <small>
                  {item.workflow_id} · {item.document_count} docs · {item.policy_tag_count} tags
                </small>
              </button>
            ))}
          </div>
        </article>
      </section>

      <section className="two-column-layout">
        <article className="panel">
          <div className="panel-label">Selected case</div>
          <h2>{selectedCase?.applicant_name ?? 'Choose a case'}</h2>
          {selectedCase ? (
            <div className="case-summary">
              <div className="summary-grid">
                <SummaryItem label="Case ID" value={selectedCase.case_id} />
                <SummaryItem label="Workflow" value={selectedCase.workflow_id} />
                <SummaryItem label="Status" value={selectedCase.status_label} />
                <SummaryItem label="Recommendation" value={selectedCase.ai_outcome ? formatLabel(selectedCase.ai_outcome) : 'Pending'} />
              </div>

              <div className="summary-block">
                <h3>AI summary</h3>
                <p>{selectedCase.ai_summary ?? 'No AI summary available yet.'}</p>
              </div>

              <div className="summary-block">
                <h3>Evidence snippets</h3>
                <div className="citation-list">
                  {selectedCase.citations.length ? (
                    selectedCase.citations.map((citation) => (
                      <article key={`${citation.source}-${citation.excerpt}`} className="citation-card">
                        <strong>{citation.source}</strong>
                        <p>{citation.excerpt}</p>
                      </article>
                    ))
                  ) : (
                    <p>No citations recorded yet.</p>
                  )}
                </div>
              </div>

              <div className="summary-block">
                <h3>Reviewer note</h3>
                <p>{selectedCase.reviewer_comment ?? 'Awaiting reviewer decision.'}</p>
              </div>
            </div>
          ) : (
            <p>Select a case on the right to inspect its live audit timeline and recommendation context.</p>
          )}
        </article>

        <article className="panel">
          <div className="panel-label">Audit trail</div>
          <h2>Event timeline</h2>
          <div className="timeline">
            {(auditEvents.length ? auditEvents : dashboard?.recent_audit_events ?? []).map((event) => (
              <article key={event.event_id} className="timeline-item">
                <div className="timeline-item__topline">
                  <strong>{formatLabel(event.action)}</strong>
                  <span>{formatTimestamp(event.occurred_at)}</span>
                </div>
                <p>{event.summary}</p>
                <small>
                  Actor: {event.actor.id} · {formatLabel(event.actor.type)}
                </small>
              </article>
            ))}
          </div>

          <div className="status-breakdown">
            <h3>Status mix</h3>
            <div className="status-tags">
              {dashboard
                ? Object.entries(dashboard.status_breakdown).map(([status, count]) => (
                    <span key={status} className="mini-pill">
                      {formatLabel(status)} · {count}
                    </span>
                  ))
                : null}
            </div>
          </div>
        </article>
      </section>

      <section className="footnote-panel">
        <span className="mini-pill">Live API-driven frontend</span>
        <span className="mini-pill">FastAPI control plane</span>
        <span className="mini-pill">Recruiter-ready architecture</span>
      </section>
    </main>
  )
}

function MetricCard({ label, value, tone }: { label: string; value: string | number; tone: 'default' | 'info' | 'success' | 'warning' | 'attention' }) {
  return (
    <article className={`metric-card metric-card--${tone}`}>
      <span>{label}</span>
      <strong>{value}</strong>
    </article>
  )
}

function SummaryItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="summary-item">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  )
}

export default App
