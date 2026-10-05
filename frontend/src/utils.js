export const fmtDate = (iso) =>
  iso ? new Date(iso).toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' }) : '—'

export const fmtDateTime = (iso) =>
  iso
    ? new Date(iso).toLocaleString(undefined, { day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' })
    : '—'

export const pct = (p, digits = 0) => `${(p * 100).toFixed(digits)}%`

// Same bands the backend uses for the dashboard risk split.
export function riskLevel(p) {
  if (p >= 0.5) return { key: 'high', label: 'Suspicious', advice: 'Recommend dermatologist review.' }
  if (p >= 0.3) return { key: 'medium', label: 'Borderline', advice: 'Monitor and consider a follow-up.' }
  return { key: 'low', label: 'Low risk', advice: 'No immediate concern flagged by the model.' }
}

export const BODY_SITES = [
  'Face', 'Scalp', 'Neck', 'Chest', 'Back', 'Abdomen', 'Upper arm', 'Forearm', 'Hand',
  'Thigh', 'Lower leg', 'Foot', 'Genital area', 'Other',
]

export const SKIN_TYPES = [
  ['1', 'I — always burns'], ['2', 'II — burns easily'], ['3', 'III — sometimes burns'],
  ['4', 'IV — rarely burns'], ['5', 'V — very rarely burns'], ['6', 'VI — never burns'],
]
