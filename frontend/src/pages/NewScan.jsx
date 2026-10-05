import { useEffect, useRef, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { listPatients, predict } from '../api'
import Icon from '../components/Icons'
import PatientForm from '../components/PatientForm'
import RiskBadge from '../components/RiskBadge'
import ScanViewer from '../components/ScanViewer'
import { BODY_SITES, pct, riskLevel } from '../utils'

export default function NewScan() {
  const [params] = useSearchParams()
  const [patients, setPatients] = useState([])
  const [patientId, setPatientId] = useState(params.get('patient') || '')
  const [bodySite, setBodySite] = useState('')
  const [notes, setNotes] = useState('')
  const [file, setFile] = useState(null)
  const [preview, setPreview] = useState(null)
  const [dragging, setDragging] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState(null)
  const [showForm, setShowForm] = useState(false)
  const inputRef = useRef(null)

  useEffect(() => { listPatients().then(setPatients).catch(() => {}) }, [])
  useEffect(() => () => preview && URL.revokeObjectURL(preview), [preview])

  const choose = (f) => {
    if (!f) return
    if (!f.type.startsWith('image/')) return setError('Please choose an image file.')
    setError('')
    setResult(null)
    setFile(f)
    setPreview(URL.createObjectURL(f))
  }

  const analyze = async (e) => {
    e.preventDefault()
    setBusy(true)
    setError('')
    try {
      setResult(await predict({ file, patient: patientId, bodySite, notes }))
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  const reset = () => { setResult(null); setFile(null); setPreview(null); setNotes(''); setBodySite('') }
  const risk = result && riskLevel(result.probability)

  return (
    <>
      <div className="page-head">
        <div><h1>New scan</h1><p className="muted">Attach the image to a patient, or run a quick scan without one.</p></div>
      </div>

      <div className="two-col scan-layout">
        <form className="card" onSubmit={analyze}>
          <label>Patient
            <div className="inline-field">
              <select value={patientId} onChange={(e) => setPatientId(e.target.value)}>
                <option value="">Quick scan (no patient)</option>
                {patients.map((p) => <option key={p.id} value={p.id}>{p.code} — {p.full_name}</option>)}
              </select>
              <button type="button" className="btn ghost" onClick={() => setShowForm(true)}><Icon name="plus" size={16} /> New</button>
            </div>
          </label>
          <label>Body site
            <select value={bodySite} onChange={(e) => setBodySite(e.target.value)}>
              <option value="">Not specified</option>
              {BODY_SITES.map((s) => <option key={s}>{s}</option>)}
            </select>
          </label>
          <label>Notes
            <textarea rows="2" placeholder="Symptoms, change in size/colour, itching…" value={notes} onChange={(e) => setNotes(e.target.value)} />
          </label>

          <div
            className={`drop ${dragging ? 'drag' : ''}`}
            role="button"
            tabIndex={0}
            onClick={() => inputRef.current.click()}
            onKeyDown={(e) => (e.key === 'Enter' || e.key === ' ') && inputRef.current.click()}
            onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
            onDragLeave={() => setDragging(false)}
            onDrop={(e) => { e.preventDefault(); setDragging(false); choose(e.dataTransfer.files[0]) }}
          >
            {preview ? <img src={preview} alt="Selected lesion" /> : (
              <div className="drop-empty"><Icon name="upload" size={28} /><strong>Drop a dermoscopy image</strong><span>or click to browse · JPG, PNG up to 10 MB</span></div>
            )}
            <input ref={inputRef} type="file" accept="image/*" hidden onChange={(e) => choose(e.target.files[0])} />
          </div>

          {error && <p className="error" role="alert">{error}</p>}
          <button className="btn primary block" disabled={!file || busy}>{busy ? 'Analyzing…' : 'Analyze image'}</button>
        </form>

        <section className="card">
          {!result ? (
            <div className="placeholder"><Icon name="scan" size={36} /><p>Results will appear here after analysis.</p></div>
          ) : (
            <>
              {!result.model_trained && <div className="notice warn"><Icon name="alert" /><span>The model has no trained weights — this result is a placeholder.</span></div>}
              <div className={`verdict ${risk.key}`}>
                <div><strong>{risk.label}</strong><span>{pct(result.probability, 1)} melanoma probability</span></div>
                <RiskBadge probability={result.probability} showPct={false} />
              </div>
              <div className="meter"><div className={risk.key} style={{ width: pct(result.probability) }} /></div>
              <p className="hint">{risk.advice}</p>
              <ScanViewer scan={result} />
              <div className="actions">
                {result.patient && <Link className="btn ghost" to={`/app/patients/${result.patient}`}>View patient</Link>}
                <Link className="btn ghost" to={`/app/scans/${result.id}`}>Open report</Link>
                <button className="btn primary" onClick={reset}>Scan another</button>
              </div>
            </>
          )}
        </section>
      </div>

      {showForm && (
        <PatientForm
          onClose={() => setShowForm(false)}
          onSaved={(p) => { setPatients([p, ...patients]); setPatientId(String(p.id)); setShowForm(false) }}
        />
      )}
    </>
  )
}
