import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { listScans } from '../api'
import Icon from '../components/Icons'
import RiskBadge from '../components/RiskBadge'
import { fmtDateTime } from '../utils'

const FILTERS = [['', 'All'], ['melanoma', 'Suspicious'], ['non-melanoma', 'Not suspicious']]

export default function History() {
  const navigate = useNavigate()
  const [filter, setFilter] = useState('')
  const [scans, setScans] = useState(null)
  const [q, setQ] = useState('')
  const [error, setError] = useState('')

  useEffect(() => {
    setScans(null)
    listScans({ label: filter }).then(setScans).catch((e) => setError(e.message))
  }, [filter])

  const shown = useMemo(() => {
    const t = q.trim().toLowerCase()
    if (!scans || !t) return scans
    return scans.filter((s) => [s.patient_name, s.patient_code, s.body_site].some((v) => v?.toLowerCase().includes(t)))
  }, [scans, q])

  return (
    <>
      <div className="page-head">
        <div><h1>Scan history</h1><p className="muted">Every analysis, newest first.</p></div>
        <Link to="/app/scan/new" className="btn primary"><Icon name="plus" size={18} /> New scan</Link>
      </div>

      <div className="toolbar">
        <div className="seg-control" role="tablist">
          {FILTERS.map(([v, label]) => (
            <button key={v} role="tab" aria-selected={filter === v} onClick={() => setFilter(v)}>{label}</button>
          ))}
        </div>
        <div className="search compact">
          <Icon name="search" size={18} />
          <input placeholder="Filter by patient or site" value={q} onChange={(e) => setQ(e.target.value)} aria-label="Filter scans" />
        </div>
      </div>
      {error && <p className="error">{error}</p>}

      <section className="card flush">
        {shown && shown.length === 0 ? (
          <p className="empty">No scans found.</p>
        ) : (
          <div className="table-wrap">
            <table>
              <thead><tr><th>Image</th><th>Patient</th><th>Body site</th><th>Result</th><th>Date</th></tr></thead>
              <tbody>
                {(shown || []).map((s) => (
                  <tr key={s.id} className="clickable" onClick={() => navigate(`/app/scans/${s.id}`)}>
                    <td><img src={s.image} alt="" className="thumb-sm" /></td>
                    <td>{s.patient ? <><strong>{s.patient_name}</strong><span className="muted small block">{s.patient_code}</span></> : <span className="muted">Quick scan</span>}</td>
                    <td>{s.body_site || '—'}</td>
                    <td><RiskBadge probability={s.probability} /></td>
                    <td>{fmtDateTime(s.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </>
  )
}
