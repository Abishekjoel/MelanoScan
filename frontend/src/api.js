const API = import.meta.env.VITE_API_URL
async function request(path, { method = 'GET', body, json } = {}) {
  const headers = {}
  if (json) headers['Content-Type'] = 'application/json'
  const res = await fetch(`${API}${path}`, {
    method,
    headers,
    body: json ? JSON.stringify(json) : body,
  })
  if (res.status === 204) return null
  const data = await res.json().catch(() => ({}))
  if (!res.ok) {
    const first = typeof data === 'object' && data ? Object.values(data)[0] : null
    const msg = data.error || data.detail || (Array.isArray(first) ? first[0] : first) || `Request failed (${res.status})`
    throw new Error(typeof msg === 'string' ? msg : 'Request failed')
  }
  return data
}

export const health = () => request('/health/')
export const stats = () => request('/stats/')

export const listPatients = (q = '') => request(`/patients/?q=${encodeURIComponent(q)}`)
export const getPatient = (id) => request(`/patients/${id}/`)
export const createPatient = (data) => request('/patients/', { method: 'POST', json: data })
export const updatePatient = (id, data) => request(`/patients/${id}/`, { method: 'PATCH', json: data })
export const deletePatient = (id) => request(`/patients/${id}/`, { method: 'DELETE' })

export const listScans = (params = {}) => {
  const qs = new URLSearchParams(Object.entries(params).filter(([, v]) => v)).toString()
  return request(`/scans/?${qs}`)
}
export const getScan = (id) => request(`/scans/${id}/`)
export const updateScan = (id, data) => request(`/scans/${id}/`, { method: 'PATCH', json: data })
export const deleteScan = (id) => request(`/scans/${id}/`, { method: 'DELETE' })

export const predict = ({ file, patient, bodySite, notes }) => {
  const body = new FormData()
  body.append('image', file)
  if (patient) body.append('patient', patient)
  if (bodySite) body.append('body_site', bodySite)
  if (notes) body.append('notes', notes)
  return request('/predict/', { method: 'POST', body })
}
