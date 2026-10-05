import { pct, riskLevel } from '../utils'

export default function RiskBadge({ probability, showPct = true }) {
  const r = riskLevel(probability)
  return (
    <span className={`badge ${r.key}`}>
      {r.label}{showPct && <em>{pct(probability)}</em>}
    </span>
  )
}
