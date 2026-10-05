import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { deletePatient, getPatient, listScans } from '../api'
import Icon from '../components/Icons'
import PatientForm from '../components/PatientForm'
import RiskBadge from '../components/RiskBadge'
import { fmtDate, fmtDateTime, SKIN_TYPES } from '../utils'

function Trend({ scans }) {
  // oldest -> newest melanoma probability
  const pts = [...scans].reverse()
  if (pts.length < 2) return null
  const x = (i) => 4 + (i / (pts.length - 1)) * 92
  const y = (p) => 30 - p * 26
  return (
    <svg viewBox="0 0 100 34" className="trend" role="img" aria-label="Melanoma probability over time">
      <line x1="4" x2="96" y1={y(0.5)} y2={y(0.5)} className="threshold" />
      <polyline points={pts.map((s, i) => `${x(i)},${y(s.probability)}`).join(' ')} className="trend-line" />
      {pts.map((s, i) => <circle key={s.id} cx={x(i)} cy={y(s.probability)} r="1.6" className="trend-dot"><title>{`${fmtDate(s.created_at)}: ${(s.probability * 100).toFixed(0)}%`}</title></circle>)}
    </svg>
  )
}

export default function PatientDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [patient, setPatient] = useState(null)
  const [scans, setScans] = useState([])
  const [error, setError] = useState('')
  const [editing, setEditing] = useState(false)

  useEffect(() => {
    getPatient(id).then(setPatient).catch((e) => setError(e.message))
    listScans({ patient: id }).then(setScans).catch(() => {})
  }, [id])

  const remove = async () => {
    if (!window.confirm(`Delete ${patient.full_name} and all ${scans.length} scan(s)? This cannot be undone.`)) return
    await deletePatient(id)
    navigate('/app/patients')
  }

  if (error) return <p className="error">{error}</p>
  if (!patient) return <p className="muted">Loading…</p>

  const skin = SKIN_TYPES.find(([v]) => v === patient.skin_type)
  const details = [
    ['Date of birth', patient.date_of_birth ? `${fmtDate(patient.date_of_birth)} (${patient.age} y)` : '—'],
    ['Sex', patient.sex ? patient.sex[0].toUpperCase() + patient.sex.slice(1) : '—'],
    ['Phone', patient.phone || '—'],
    ['Email', patient.email || '—'],
    ['Skin type', skin ? skin[1] : 'Unknown'],
    ['Registered', fmtDate(patient.created_at)],
  ]

  return (
    <>
      <Link to="/app/patients" className="back">← Patients</Link>
      <div className="page-head">
        <div className="head-id">
          <span className="avatar lg">{patient.full_name[0]?.toUpperCase()}</span>
          <div><h1>{patient.full_name}</h1><p className="muted">{patient.code}</p></div>
        </div>
        <div className="actions">
          <button className="btn ghost" onClick={() => setEditing(true)}><Icon name="edit" size={16} /> Edit</button>
          <button className="btn ghost danger" onClick={remove}><Icon name="trash" size={16} /> Delete</button>
          <Link to={`/app/scan/new?patient=${patient.id}`} className="btn primary"><Icon name="scan" size={18} /> New scan</Link>
        </div>
      </div>

      <div className="two-col detail-layout">
        <section className="card">
          <h2>Details</h2>
          <dl className="kv">{details.map(([k, v]) => <div key={k}><dt>{k}</dt><dd>{v}</dd></div>)}</dl>
          <h3>Medical history</h3>
          <p className="prose">{patient.medical_history || <span className="muted">None recorded.</span>}</p>
          <h3>Notes</h3>
          <p className="prose">{patient.notes || <span className="muted">None.</span>}</p>
        </section>

        <section className="card">
          <div className="card-head"><h2>Scans ({scans.length})</h2></div>
          <Trend scans={scans} />
          {scans.length === 0 ? (
            <p className="muted">No scans for this patient yet.</p>
          ) : (
            <ul className="list">
              {scans.map((s) => (
                <li key={s.id}>
                  <Link to={`/app/scans/${s.id}`} className="row-link">
                    <img src={s.image} alt="" className="thumb-sm" />
                    <div className="grow">
                      <strong>{s.body_site || 'Site not set'}</strong>
                      <span className="muted small">{fmtDateTime(s.created_at)}</span>
                    </div>
                    <RiskBadge probability={s.probability} />
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>

      {editing && <PatientForm patient={patient} onClose={() => setEditing(false)} onSaved={(p) => { setPatient({ ...patient, ...p }); setEditing(false) }} />}
    </>
  )
}
