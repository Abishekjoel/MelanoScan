import { NavLink, Outlet } from 'react-router-dom'
import Icon from './Icons'

const NAV = [
  ['/app', 'Dashboard', 'home', true],
  ['/app/scan/new', 'New scan', 'scan'],
  ['/app/patients', 'Patients', 'users'],
  ['/app/history', 'History', 'history'],
]

export function Brand({ to = '/' }) {
  return (
    <NavLink to={to} className="brand">
      <span className="brand-mark"><Icon name="target" size={18} /></span>
      <span>Melano<b>Scan</b></span>
    </NavLink>
  )
}

export default function Layout() {
  return (
    <div className="shell">
      <aside className="sidebar">
        <Brand to="/app" />
        <nav>
          {NAV.map(([to, label, icon, end]) => (
            <NavLink key={to} to={to} end={end} className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
              <Icon name={icon} /> <span>{label}</span>
            </NavLink>
          ))}
        </nav>
      </aside>
      <main className="content">
        <Outlet />
        <p className="footnote">Research prototype — not a medical device and not a diagnosis. Always consult a dermatologist.</p>
      </main>
    </div>
  )
}
