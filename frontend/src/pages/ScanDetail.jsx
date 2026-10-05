import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { deleteScan, getScan, updateScan } from '../api'
import Icon from '../components/Icons'
import ScanViewer from '../components/ScanViewer'
import { BODY_SITES, fmtDateTime, pct, riskLevel } from '../utils'

export default function ScanDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [scan, setScan] = useState(null)
  const [notes, setNotes] = useState('')
  const [site, setSite] = useState('')
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    getScan(id).then((s) => { setScan(s); setNotes(s.notes); setSite(s.body_site) }).catch((e) => setError(e.message))
  }, [id])

  const save = async () => {
    try {
      setScan(await updateScan(id, { notes, body_site: site }))
      setSaved(true)
      setTimeout(() => setSaved(false), 2000)
    } catch (e) {
      setError(e.message)
    }
  }

  const remove = async () => {
    if (!window.confirm('Delete this scan permanently?')) return
    await deleteScan(id)
    navigate(scan.patient ? `/app/patients/${scan.patient}` : '/app/history')
  }

  if (error) return <p className="error">{error}</p>
  if (!scan) return <p className="muted">Loading…</p>
  const risk = riskLevel(scan.probability)

  return (
    <>
      <Link to={scan.patient ? `/app/patients/${scan.patient}` : '/app/history'} className="back no-print">← Back</Link>
      <div className="page-head">
        <div><h1>Scan report</h1><p className="muted">{fmtDateTime(scan.created_at)}</p></div>
        <div className="actions no-print">
          <button className="btn ghost" onClick={() => window.print()}><Icon name="print" size={16} /> Print</button>
          <button className="btn ghost danger" onClick={remove}><Icon name="trash" size={16} /> Delete</button>
        </div>
      </div>

      <div className="two-col scan-layout">
        <section className="card"><ScanViewer scan={scan} /></section>
        <section className="card">
          {!scan.model_trained && <div className="notice warn"><Icon name="alert" /><span>Recorded with an untrained model — placeholder result.</span></div>}
          <div className={`verdict ${risk.key}`}>
            <div><strong>{risk.label}</strong><span>{pct(scan.probability, 1)} melanoma probability</span></div>
          </div>
          <div className="meter"><div className={risk.key} style={{ width: pct(scan.probability) }} /></div>
          <p className="hint">{risk.advice}</p>

          <dl className="kv">
            <div><dt>Patient</dt><dd>{scan.patient ? <Link className="link" to={`/app/patients/${scan.patient}`}>{scan.patient_name} ({scan.patient_code})</Link> : 'Quick scan'}</dd></div>
          </dl>
          <label className="no-print">Body site
            <select value={site} onChange={(e) => setSite(e.target.value)}>
              <option value="">Not specified</option>
              {BODY_SITES.map((s) => <option key={s}>{s}</option>)}
            </select>
          </label>
          <p className="print-only">Body site: {scan.body_site || 'Not specified'}</p>
          <label>Clinical notes
            <textarea rows="4" value={notes} onChange={(e) => setNotes(e.target.value)} />
          </label>
          <div className="actions no-print">
            <button className="btn primary" onClick={save}>{saved ? 'Saved ✓' : 'Save notes'}</button>
          </div>
          <p className="hint">AI output is a screening aid only and does not constitute a diagnosis.</p>
        </section>
      </div>
    </>
  )
}
