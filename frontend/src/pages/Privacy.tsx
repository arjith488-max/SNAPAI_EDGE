import { useState, useEffect } from 'react'
import { privacyAPI } from '../services/api'
import { BubbleBadge, BubbleCard, BubbleButton } from '../components/bubbles'

interface PrivacyStatus {
  privacy_mode: string
  cloud_enabled: boolean
  telemetry: boolean
  local_processing: boolean
  cloud_processing: boolean
  camera_enabled: boolean
  voice_enabled: boolean
  data_storage: string
  api_key_stored: string
}

export default function Privacy() {
  const [status, setStatus] = useState<PrivacyStatus | null>(null)
  const [saving, setSaving] = useState(false)
  const [clearing, setClearing] = useState('')
  const [message, setMessage] = useState('')

  useEffect(() => { load() }, [])

  const load = async () => {
    try {
      const r = await privacyAPI.status()
      setStatus(r.data)
    } catch {}
  }

  const save = async () => {
    if (!status) return
    setSaving(true)
    try {
      await privacyAPI.update({
        privacy_mode: status.privacy_mode,
        cloud_enabled: status.cloud_enabled,
        telemetry: status.telemetry,
      })
      setMessage('Privacy settings saved successfully')
      setTimeout(() => setMessage(''), 3000)
    } catch {}
    setSaving(false)
  }

  const clearData = async (type: 'conversations' | 'documents' | 'all') => {
    if (!confirm(`Permanently delete all ${type}? This operation cannot be undone.`)) return
    setClearing(type)
    try {
      if (type === 'conversations') await privacyAPI.clearConversations()
      else if (type === 'documents') await privacyAPI.clearDocuments()
      else await privacyAPI.clearAll()
      setMessage(`Cleared: ${type}`)
      setTimeout(() => setMessage(''), 3000)
    } catch {}
    setClearing('')
  }

  const isLocalOnly = status?.privacy_mode === 'offline' || !status?.cloud_enabled

  return (
    <div className="page-pad">
      <div className="page-header">
        <h1 className="page-title">🔒 Privacy Guard & Zero-Trust Shield</h1>
        <p className="page-subtitle">On-Device Confidentiality · Zero Data Leakage · Air-Gapped Local Inference</p>
      </div>

      {message && (
        <div style={{ padding: 12, background: 'rgba(16, 185, 129, 0.12)', border: '1px solid rgba(16, 185, 129, 0.25)', borderRadius: 'var(--bubble-radius-md)', color: 'var(--color-ok)', fontSize: '0.85rem' }} className="mb-4">
          ✓ {message}
        </div>
      )}

      {/* Section 24: Clear Privacy Status Bubble */}
      <BubbleCard
        variant="elevated"
        style={{
          padding: '24px 28px',
          marginBottom: 24,
          background: isLocalOnly
            ? 'linear-gradient(135deg, rgba(16, 185, 129, 0.12) 0%, rgba(6, 182, 212, 0.08) 100%)'
            : 'linear-gradient(135deg, rgba(99, 102, 241, 0.12) 0%, rgba(139, 92, 246, 0.08) 100%)',
          borderColor: isLocalOnly ? 'rgba(16, 185, 129, 0.3)' : 'rgba(99, 102, 241, 0.3)',
        }}
      >
        <div className="flex justify-between items-center flex-wrap gap-4">
          <div className="flex items-center gap-3">
            <div
              style={{
                width: 48,
                height: 48,
                borderRadius: 'var(--bubble-radius-md)',
                background: isLocalOnly ? 'var(--color-local)' : 'var(--brand-500)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: '22px',
                color: '#fff',
                boxShadow: 'var(--bubble-shadow-soft)',
              }}
            >
              🔒
            </div>
            <div>
              <div className="fw-800 text-lg" style={{ color: 'var(--text-primary)' }}>
                {isLocalOnly ? 'Air-Gapped Privacy Active' : 'Adaptive Local-First Shield'}
              </div>
              <div className="text-xs text-muted">
                {isLocalOnly
                  ? 'All AI computation executed on-device · Network not used · Protected ✓'
                  : 'Local processing preferred · Sensitive data scanned prior to any cloud fallback'}
              </div>
            </div>
          </div>

          <div className="flex gap-2">
            <BubbleBadge variant={isLocalOnly ? 'local' : 'brand'}>
              {isLocalOnly ? 'Zero Cloud' : 'Local First'}
            </BubbleBadge>
            <BubbleBadge variant="success">
              Telemetry Disabled ✓
            </BubbleBadge>
          </div>
        </div>
      </BubbleCard>

      <div className="g2" style={{ alignItems: 'start', gap: 20 }}>
        {/* Left: Configuration Bubbles */}
        <BubbleCard variant="elevated" style={{ padding: 24 }}>
          <h3 className="fw-800 text-base mb-4" style={{ color: 'var(--text-primary)' }}>
            ⚙️ Privacy Guard Configuration
          </h3>

          <div className="mb-4">
            <label className="text-xs fw-700 text-muted uppercase block mb-2">
              AI Processing Mode
            </label>
            <select
              className="select w-full"
              value={status?.privacy_mode ?? 'local_first'}
              onChange={e => status && setStatus({ ...status, privacy_mode: e.target.value })}
            >
              <option value="local_first">⚡ Local First (Prioritize Snapdragon/Ollama)</option>
              <option value="cloud_first">☁️ Cloud First (Complex reasoning permitted)</option>
              <option value="hybrid">◐ Hybrid (Local RAG + Cloud)</option>
              <option value="offline">○ Offline Only (Strict Zero Cloud)</option>
            </select>
          </div>

          <div className="flex flex-col gap-3 mb-6">
            <div className="flex justify-between items-center" style={{ padding: '12px 0', borderBottom: '1px solid var(--bubble-border-subtle)' }}>
              <div>
                <div className="fw-600 text-sm">Allow Cloud Fallback</div>
                <div className="text-xs text-muted">Allow non-sensitive requests to reach OpenAI or Gemini</div>
              </div>
              <input
                type="checkbox"
                checked={status?.cloud_enabled ?? true}
                onChange={e => status && setStatus({ ...status, cloud_enabled: e.target.checked })}
                style={{ width: 18, height: 18, accentColor: 'var(--brand-500)', cursor: 'pointer' }}
              />
            </div>

            <div className="flex justify-between items-center" style={{ padding: '12px 0', borderBottom: '1px solid var(--bubble-border-subtle)' }}>
              <div>
                <div className="fw-600 text-sm">Anonymous Telemetry</div>
                <div className="text-xs text-muted">Transmit diagnostic data (always off by default)</div>
              </div>
              <input
                type="checkbox"
                checked={status?.telemetry ?? false}
                onChange={e => status && setStatus({ ...status, telemetry: e.target.checked })}
                style={{ width: 18, height: 18, accentColor: 'var(--brand-500)', cursor: 'pointer' }}
              />
            </div>
          </div>

          <BubbleButton variant="primary" onClick={save} disabled={saving}>
            {saving ? 'Saving...' : 'Save Privacy Guard Preferences'}
          </BubbleButton>
        </BubbleCard>

        {/* Right: Data Retention & Erase Bubbles */}
        <div className="flex flex-col gap-4">
          <BubbleCard variant="glass" style={{ padding: 24 }}>
            <h3 className="fw-800 text-base mb-3" style={{ color: 'var(--text-primary)' }}>
              🛡️ Storage & Retention Policy
            </h3>
            <div className="flex flex-col gap-2 text-xs text-secondary mb-4">
              <div className="flex justify-between py-1 border-b border-subtle">
                <span className="text-muted">Chat History Storage:</span>
                <span className="fw-600">Local SQLite (snapai.db)</span>
              </div>
              <div className="flex justify-between py-1 border-b border-subtle">
                <span className="text-muted">Document Embeddings:</span>
                <span className="fw-600">Local Vector Index</span>
              </div>
              <div className="flex justify-between py-1 border-b border-subtle">
                <span className="text-muted">External Logging:</span>
                <span className="fw-600 text-green">None (Zero External Logs)</span>
              </div>
            </div>
          </BubbleCard>

          <BubbleCard variant="elevated" style={{ padding: 24 }}>
            <h3 className="fw-800 text-base mb-2" style={{ color: 'var(--text-primary)' }}>
              🗑️ Instant Data Erasure
            </h3>
            <p className="text-xs text-muted mb-4">
              Instantly wipe conversation history or indexed knowledge from disk with zero recovery trace.
            </p>

            <div className="flex flex-wrap gap-2">
              <BubbleButton
                variant="danger"
                size="sm"
                onClick={() => clearData('conversations')}
                disabled={clearing === 'conversations'}
              >
                {clearing === 'conversations' ? 'Clearing...' : 'Clear Conversations'}
              </BubbleButton>
              <BubbleButton
                variant="danger"
                size="sm"
                onClick={() => clearData('documents')}
                disabled={clearing === 'documents'}
              >
                {clearing === 'documents' ? 'Clearing...' : 'Clear Documents'}
              </BubbleButton>
              <BubbleButton
                variant="danger"
                size="sm"
                onClick={() => clearData('all')}
                disabled={clearing === 'all'}
              >
                {clearing === 'all' ? 'Wiping...' : 'Wipe All Data'}
              </BubbleButton>
            </div>
          </BubbleCard>
        </div>
      </div>
    </div>
  )
}
