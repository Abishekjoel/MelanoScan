import { Link } from 'react-router-dom'
import { Brand } from '../components/Layout'
import Icon from '../components/Icons'

const FEATURES = [
  ['target', 'Lesion detection', 'A segmentation network outlines the lesion and draws a bounding box, so you can see exactly what was analyzed.'],
  ['shield', 'Melanoma risk score', 'A dual-backbone fusion model estimates melanoma probability and bands it into low, borderline or suspicious.'],
  ['eye', 'Explainable heatmaps', 'Grad-CAM overlays show which regions pushed the score up, so results are not a black box.'],
  ['folder', 'Patient records', 'Keep patient details, skin type and history together with every scan, and review change over time.'],
]

const STEPS = [
  ['Add a patient', 'Record basic details, skin type and medical history — or run a quick anonymous scan.'],
  ['Upload a dermoscopy image', 'Drag in a photo from a dermatoscope. Results come back in seconds.'],
  ['Review and follow up', 'Inspect the outline and heatmap, add notes, and track the patient over time.'],
]

export default function Landing() {
  return (
    <div className="landing">
      <header className="nav">
        <Brand />
        <div className="nav-actions">
          <a href="#features" className="nav-text">Features</a>
          <a href="#how" className="nav-text">How it works</a>
          <Link to="/app" className="btn primary small">Open dashboard</Link>
        </div>
      </header>

      <section className="hero">
        <div className="hero-copy">
          <span className="pill">AI-assisted dermatology screening</span>
          <h1>Spot suspicious skin lesions <span className="grad">earlier</span>.</h1>
          <p>
            MelanoScan analyzes dermoscopic images with a deep-learning fusion model, highlights the lesion,
            explains its reasoning, and keeps every patient’s scans organized in one place.
          </p>
          <div className="hero-cta">
            <Link to="/app/scan/new" className="btn primary large">Start a scan <Icon name="arrow" size={18} /></Link>
            <a href="#how" className="btn ghost large">See how it works</a>
          </div>
          <ul className="hero-stats">
            <li><b>0.90</b><span>validation AUC on HAM10000</span></li>
            <li><b>10,015</b><span>dermoscopy images trained on</span></li>
            <li><b>Grad-CAM</b><span>explainable output</span></li>
          </ul>
        </div>
        <div className="hero-art" aria-hidden="true">
          <div className="lens"><div className="lens-ring" /><div className="lesion" /><div className="lesion-box" /></div>
          <div className="float-card c1"><Icon name="check" size={16} /> Lesion detected</div>
          <div className="float-card c2"><span className="dot med" /> Borderline · 38%</div>
        </div>
      </section>

      <section id="features" className="section">
        <h2>Everything for a screening workflow</h2>
        <div className="feature-grid">
          {FEATURES.map(([icon, title, text]) => (
            <article key={title} className="feature">
              <span className="feature-icon"><Icon name={icon} size={22} /></span>
              <h3>{title}</h3>
              <p>{text}</p>
            </article>
          ))}
        </div>
      </section>

      <section id="how" className="section alt">
        <h2>How it works</h2>
        <ol className="steps">
          {STEPS.map(([title, text], i) => (
            <li key={title}><span className="step-n">{i + 1}</span><h3>{title}</h3><p>{text}</p></li>
          ))}
        </ol>
      </section>

      <section className="section cta-band">
        <h2>Ready to try it?</h2>
        <Link to="/app" className="btn primary large">Open dashboard</Link>
      </section>

      <footer className="landing-foot">
        <p><Icon name="alert" size={16} /> MelanoScan is a research prototype. It is not a medical device, does not provide a diagnosis, and must not replace examination by a qualified dermatologist.</p>
        <p className="muted">Model trained on HAM10000 — public data that under-represents darker skin tones, so accuracy may be lower for Fitzpatrick types V–VI.</p>
      </footer>
    </div>
  )
}
