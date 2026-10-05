import { useState } from 'react'

export default function ScanViewer({ scan }) {
  const [mode, setMode] = useState('original')
  const src = mode === 'heatmap' && scan.heatmap ? scan.heatmap : scan.image
  return (
    <div>
      <div className="tabs" role="tablist">
        <button role="tab" aria-selected={mode === 'original'} onClick={() => setMode('original')}>Lesion detection</button>
        <button role="tab" aria-selected={mode === 'heatmap'} onClick={() => setMode('heatmap')}>Grad-CAM heatmap</button>
      </div>
      <div className="viewer">
        <img src={src} alt={mode === 'heatmap' ? 'Model attention heatmap' : 'Analyzed lesion'} />
        {mode === 'original' && scan.box && (
          <svg className="overlay" viewBox="0 0 1 1" preserveAspectRatio="none" aria-hidden="true">
            {scan.outline && <polygon points={scan.outline.map(([x, y]) => `${x},${y}`).join(' ')} className="outline" />}
            <rect x={scan.box.x} y={scan.box.y} width={scan.box.w} height={scan.box.h} className="bbox" />
          </svg>
        )}
      </div>
      <p className="hint">
        {mode === 'heatmap'
          ? 'Warmer regions pushed the melanoma score up. This is not a lesion outline.'
          : scan.box
            ? 'Yellow box and cyan outline: automatically detected lesion area.'
            : 'No lesion area was detected with enough confidence.'}
      </p>
    </div>
  )
}
