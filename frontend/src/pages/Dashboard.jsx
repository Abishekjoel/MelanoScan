import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { health, stats } from '../api'
import Icon from '../components/Icons'
import RiskBadge from '../components/RiskBadge'
import { fmtDateTime, pct } from '../utils'

function BarChart({ data }) {
  const max = Math.max(1, ...data.map((d) => d.count))
  const w = 100 / data.length
  return (
    <svg viewBox="0 0 100 44" className="bar-chart" role="img" aria-label="Scans per day, last 14 days">
      {data.map((d, i) => {
        const h = (d.count / max) * 34
        return (
          <g key={d.date}>
            <rect x={i * w + w * 0.18} y={36 - h} width={w * 0.64} height={Math.max(h, 0.8)} rx="0.8" className={d.count ? 'bar' : 'bar empty'}>
              <title>{`${d.date}: ${d.count} scan(s)`}</title>
            </rect>
            {(i % 3 === 0 || i === data.length - 1) && (
              <text x={i * w + w / 2} y="42" textAnchor="middle" className="axis">{d.date.slice(8)}</text>
            )}
          </g>
        )
      })}
    </svg>
  )
}

function RiskSplit({ risk }) {
  const total = risk.low + risk.medium + risk.high
  const rows = [['low', 'Low risk', risk.low], ['medium', 'Borderline', risk.medium], ['high', 'Suspicious', risk.high]]
  return (
    <div>
      <div className="split-bar" aria-hidden="true">
        {total === 0 ? <span className="seg empty" style={{ width: '100%' }} /> : rows.map(([k, , n]) => n > 0 && <span key={k} className={`seg ${k}`} style={{ width: `${(n / total) * 100}%` }} />)}
      </div>
      <ul className="legend">
        {rows.map(([k, label, n]) => (
          <li key={k}><span className={`dot ${k === 'medium' ? 'med' : k}`} />{label}<b>{n}</b></li>
        ))}
      </ul>
    </div>
  )
}

export default function Dashboard() {
  const [data, setData] = useState(null)
  const [status, setStatus] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    stats().then(setData).catch((e) => setError(e.message))
    health().then(setStatus).catch(() => {})
  }, [])

  if (error) return <p className="error">{error}</p>
  if (!data) return <p className="muted">Loading dashboard…</p>

  const cards = [
    ['Patients', data.patients, 'users'],
    ['Total scans', data.scans, 'scan'],
    ['Last 7 days', data.scans_7d, 'history'],
    ['Flagged suspicious', data.flagged, 'alert', pct(data.flagged_rate) + ' of scans'],
  ]

  return (
    <>
      <div className="page-head">
        <div><h1>Dashboard</h1><p className="muted">Overview of screening activity.</p></div>
        <Link to="/app/scan/new" className="btn primary"><Icon name="plus" size={18} /> New scan</Link>
      </div>

      {status && (!status.model_trained || !status.segmentation) && (
        <div className="notice warn">
          <Icon name="alert" />
          <span>
            {!status.model_trained
              ? 'The classification model has no trained weights — results are placeholders.'
              : 'Lesion segmentation weights were not found — lesion boxes will be hidden.'}
          </span>
        </div>
      )}

      <div className="stat-grid">
        {cards.map(([label, value, icon, sub]) => (
          <div key={label} className="card stat">
            <span className="stat-icon"><Icon name={icon} /></span>
            <div><div className="stat-value">{value}</div><div className="stat-label">{label}</div>{sub && <div className="stat-sub">{sub}</div>}</div>
          </div>
        ))}
      </div>

      <div className="two-col">
        <section className="card">
          <h2>Scans per day <span className="muted small">last 14 days</span></h2>
          <BarChart data={data.per_day} />
        </section>
        <section className="card">
          <h2>Risk distribution</h2>
          <RiskSplit risk={data.risk} />
        </section>
      </div>

      <section className="card">
        <div className="card-head"><h2>Recent scans</h2><Link to="/app/history" className="link">View all</Link></div>
        {data.recent.length === 0 ? (
          <p className="muted">No scans yet. <Link to="/app/scan/new" className="link">Run your first scan</Link>.</p>
        ) : (
          <ul className="list">
            {data.recent.map((s) => (
              <li key={s.id}>
                <Link to={`/app/scans/${s.id}`} className="row-link">
                  <img src={s.image} alt="" className="thumb-sm" />
                  <div className="grow">
                    <strong>{s.patient_name || 'Quick scan'}</strong>
                    <span className="muted small">{s.patient_code ? `${s.patient_code} · ` : ''}{s.body_site || 'Site not set'} · {fmtDateTime(s.created_at)}</span>
                  </div>
                  <RiskBadge probability={s.probability} />
                </Link>
              </li>
            ))}
          </ul>
        )}
      </section>
    </>
  )
}
