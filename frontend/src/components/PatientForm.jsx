import { useState } from 'react'
import { createPatient, updatePatient } from '../api'
import { SKIN_TYPES } from '../utils'
import Icon from './Icons'

const EMPTY = { full_name: '', date_of_birth: '', sex: '', phone: '', email: '', skin_type: '', medical_history: '', notes: '' }

export default function PatientForm({ patient, onSaved, onClose }) {
  const [form, setForm] = useState(patient ? { ...EMPTY, ...patient } : EMPTY)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value })

  const submit = async (e) => {
    e.preventDefault()
    setSaving(true)
    setError('')
    const data = Object.fromEntries(
      Object.keys(EMPTY).map((k) => [k, k === 'date_of_birth' && !form[k] ? null : form[k]]),
    )
    try {
      onSaved(patient ? await updatePatient(patient.id, data) : await createPatient(data))
    } catch (err) {
      setError(err.message)
      setSaving(false)
    }
  }

  return (
    <div className="modal-backdrop" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <form className="modal" onSubmit={submit} role="dialog" aria-modal="true" aria-label={patient ? 'Edit patient' : 'New patient'}>
        <div className="modal-head">
          <h2>{patient ? 'Edit patient' : 'New patient'}</h2>
          <button type="button" className="icon-btn" onClick={onClose} aria-label="Close"><Icon name="close" /></button>
        </div>
        <div className="form-grid">
          <label className="span-2">Full name *
            <input required autoFocus value={form.full_name} onChange={set('full_name')} />
          </label>
          <label>Date of birth
            <input type="date" max={new Date().toISOString().slice(0, 10)} value={form.date_of_birth || ''} onChange={set('date_of_birth')} />
          </label>
          <label>Sex
            <select value={form.sex} onChange={set('sex')}>
              <option value="">—</option><option value="female">Female</option><option value="male">Male</option><option value="other">Other</option>
            </select>
          </label>
          <label>Phone
            <input type="tel" value={form.phone} onChange={set('phone')} />
          </label>
          <label>Email
            <input type="email" value={form.email} onChange={set('email')} />
          </label>
          <label className="span-2">Skin type (Fitzpatrick)
            <select value={form.skin_type} onChange={set('skin_type')}>
              <option value="">Unknown</option>
              {SKIN_TYPES.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
            </select>
          </label>
          <label className="span-2">Medical history
            <textarea rows="3" placeholder="Previous skin cancer, family history, sun exposure…" value={form.medical_history} onChange={set('medical_history')} />
          </label>
          <label className="span-2">Notes
            <textarea rows="2" value={form.notes} onChange={set('notes')} />
          </label>
        </div>
        {error && <p className="error" role="alert">{error}</p>}
        <div className="modal-foot">
          <button type="button" className="btn ghost" onClick={onClose}>Cancel</button>
          <button className="btn primary" disabled={saving}>{saving ? 'Saving…' : patient ? 'Save changes' : 'Create patient'}</button>
        </div>
      </form>
    </div>
  )
}
