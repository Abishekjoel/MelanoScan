import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import History from './pages/History'
import Landing from './pages/Landing'
import NewScan from './pages/NewScan'
import PatientDetail from './pages/PatientDetail'
import Patients from './pages/Patients'
import ScanDetail from './pages/ScanDetail'

export default function App() {
  return (
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Landing />} />
          <Route path="/app" element={<Layout />}>
            <Route index element={<Dashboard />} />
            <Route path="scan/new" element={<NewScan />} />
            <Route path="patients" element={<Patients />} />
            <Route path="patients/:id" element={<PatientDetail />} />
            <Route path="history" element={<History />} />
            <Route path="scans/:id" element={<ScanDetail />} />
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
  )
}
