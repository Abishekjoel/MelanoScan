import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { listPatients } from '../api'
import Icon from '../components/Icons'
import PatientForm from '../components/PatientForm'
import RiskBadge from '../components/RiskBadge'
import { fmtDate } from '../utils'

export default function Patients() {
  const navigate = useNavigate()
  const [patients, setPatients] = useState(null)
  const [q, setQ] = useState('')
  const [error, setError] = useState('')
  const [showForm, setShowForm] = useState(false)

  useEffect(() => {
    const t = setTimeout(() => {
      listPatients(q).then(setPatients).catch((e) => setError(e.message))
    }, 250)
    return () => clearTimeout(t)
  }, [q])

  return (
    <>
      <div className="page-head">
        <div><h1>Patients</h1><p className="muted">{patients ? `${patients.length} record${patients.length === 1 ? '' : 's'}` : 'Loading…'}</p></div>
        <button className="btn primary" onClick={() => setShowForm(true)}><Icon name="plus" size={18} /> Add patient</button>
      </div>

      <div className="search">
        <Icon name="search" size={18} />
        <input placeholder="Search by name, phone or ID (e.g. P-00012)" value={q} onChange={(e) => setQ(e.target.value)} aria-label="Search patients" />
      </div>
      {error && <p className="error">{error}</p>}

      <section className="card flush">
        {patients && patients.length === 0 ? (
          <p className="empty">{q ? 'No patients match your search.' : 'No patients yet. Add your first patient to get started.'}</p>
        ) : (
          <div className="table-wrap">
            <table>
              <thead><tr><th>Patient</th><th>Age / Sex</th><th>Contact</th><th>Scans</th><th>Latest result</th><th>Added</th></tr></thead>
              <tbody>
                {(patients || []).map((p) => (
                  <tr key={p.id} className="clickable" onClick={() => navigate(`/app/patients/${p.id}`)}>
                    <td>
                      <Link to={`/app/patients/${p.id}`} className="cell-main" onClick={(e) => e.stopPropagation()}>
                        <span className="avatar sm">{p.full_name[0]?.toUpperCase()}</span>
                        <span><strong>{p.full_name}</strong><span className="muted small block">{p.code}</span></span>
                      </Link>
                    </td>
                    <td>{p.age ?? '—'}{p.sex ? ` · ${p.sex[0].toUpperCase() + p.sex.slice(1)}` : ''}</td>
                    <td>{p.phone || p.email || '—'}</td>
                    <td>{p.scan_count}</td>
                    <td>{p.last_scan ? <RiskBadge probability={p.last_scan.probability} /> : <span className="muted">No scans</span>}</td>
                    <td>{fmtDate(p.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {showForm && <PatientForm onClose={() => setShowForm(false)} onSaved={(p) => navigate(`/app/patients/${p.id}`)} />}
    </>
  )
}
