import { useState, useEffect, useCallback } from 'react'
import { aiAPI, ProviderItem } from '../services/api'
import { useApp } from '../hooks/useAppContext'
import { BubbleBadge, BubbleCard, BubbleButton, BubbleModal } from '../components/bubbles'

export default function Settings() {
  const { theme, setTheme, resolvedTheme } = useApp()
  const [activeTab, setActiveTab] = useState<'providers' | 'general' | 'about'>('providers')
  const [saved, setSaved] = useState(false)
  const [providers, setProviders] = useState<ProviderItem[]>([])
  const [testingProvider, setTestingProvider] = useState<string | null>(null)
  const [testResults, setTestResults] = useState<Record<string, any>>({})
  const [configModalProvider, setConfigModalProvider] = useState<string | null>(null)

  const loadProviders = useCallback(async () => {
    try {
      const res = await aiAPI.providers()
      setProviders(res.data.providers || [])
    } catch {}
  }, [])

  useEffect(() => {
    loadProviders()
  }, [loadProviders])

  const handleTestConnection = async (providerId: string) => {
    setTestingProvider(providerId)
    try {
      const res = await aiAPI.testProvider(providerId)
      setTestResults(prev => ({ ...prev, [providerId]: res.data }))
    } catch (err: any) {
      setTestResults(prev => ({
        ...prev,
        [providerId]: { success: false, error: err.message },
      }))
    } finally {
      setTestingProvider(null)
      loadProviders()
    }
  }

  const handleSave = () => {
    setSaved(true)
    setTimeout(() => setSaved(false), 2500)
  }

  return (
    <div className="page-pad">
      {/* Header */}
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <h1 className="page-title">⚙️ Workspace Settings & AI Fleet</h1>
          <p className="page-subtitle">Configure intelligence providers, edge runtime, theme appearance, and security policies</p>
        </div>
        {activeTab === 'general' && (
          <BubbleButton variant="primary" onClick={handleSave}>
            {saved ? '✓ Preferences Saved' : 'Save Preferences'}
          </BubbleButton>
        )}
      </div>

      {/* Bubble Tabs */}
      <div className="flex gap-2 mb-4">
        {[
          { id: 'providers', label: '🤖 AI Fleet Providers' },
          { id: 'general',   label: '⚙️ Workspace & Theme' },
          { id: 'about',     label: 'ℹ️ About System' },
        ].map(tab => (
          <BubbleButton
            key={tab.id}
            variant={activeTab === tab.id ? 'primary' : 'secondary'}
            size="sm"
            pill
            onClick={() => setActiveTab(tab.id as any)}
          >
            {tab.label}
          </BubbleButton>
        ))}
      </div>

      {/* ── TAB 1: AI Providers Management ────────────────────── */}
      {activeTab === 'providers' && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: 16 }}>
          {providers.map(p => {
            const test = testResults[p.provider]
            const isTesting = testingProvider === p.provider

            return (
              <BubbleCard key={p.provider} variant="elevated" style={{ padding: 22, display: 'flex', flexDirection: 'column' }}>
                <div className="flex justify-between items-start mb-3">
                  <div>
                    <div className="flex items-center gap-2">
                      <h3 className="fw-800 text-base" style={{ margin: 0, color: 'var(--text-primary)' }}>
                        {p.name}
                      </h3>
                      <BubbleBadge variant={p.available ? 'local' : 'neutral'} size="sm">
                        {p.available ? (p.type === 'local' ? 'RUNNING' : 'ONLINE') : 'OFFLINE'}
                      </BubbleBadge>
                    </div>
                    <div className="text-xs text-muted mt-1">
                      {p.type === 'local' ? 'On-Device Edge Engine' : 'Cloud Intelligence API'}
                    </div>
                  </div>
                  <div style={{ fontSize: '1.6rem' }}>
                    {p.provider === 'openai' ? '🟢' : p.provider === 'gemini' ? '🔷' : p.provider === 'ollama' ? '🦙' : '⚡'}
                  </div>
                </div>

                <div style={{ flex: 1, padding: '12px 0', borderTop: '1px solid var(--bubble-border-subtle)', fontSize: '0.82rem' }}>
                  <div className="flex justify-between py-1">
                    <span className="text-muted">Status:</span>
                    <span className="fw-600">{p.status_text}</span>
                  </div>
                  <div className="flex justify-between py-1">
                    <span className="text-muted">Active Model:</span>
                    <span className="fw-600">{p.active_model || 'N/A'}</span>
                  </div>
                  {p.type === 'local' && (
                    <div className="flex justify-between py-1">
                      <span className="text-muted">Installed Models:</span>
                      <span className="fw-700 text-brand">{p.models_count}</span>
                    </div>
                  )}
                  <div className="flex justify-between py-1">
                    <span className="text-muted">Endpoint:</span>
                    <span className="text-xs text-secondary font-mono truncate" style={{ maxWidth: 180 }}>{p.endpoint || 'N/A'}</span>
                  </div>
                  {p.latency_ms !== undefined && p.latency_ms !== null && (
                    <div className="flex justify-between py-1">
                      <span className="text-muted">Measured Latency:</span>
                      <span className="fw-700 text-green">{p.latency_ms} ms</span>
                    </div>
                  )}

                  {test && (
                    <div
                      style={{
                        marginTop: 10,
                        padding: '8px 12px',
                        borderRadius: 'var(--bubble-radius-md)',
                        fontSize: '0.78rem',
                        background: test.success ? 'rgba(16, 185, 129, 0.12)' : 'rgba(239, 68, 68, 0.12)',
                        border: `1px solid ${test.success ? 'rgba(16, 185, 129, 0.25)' : 'rgba(239, 68, 68, 0.25)'}`,
                        color: test.success ? '#10b981' : '#ef4444',
                      }}
                    >
                      {test.success ? (
                        <div>✓ Connection verified ({test.latency_ms} ms latency)</div>
                      ) : (
                        <div>✗ Test error: {test.error || 'Connection failed'}</div>
                      )}
                    </div>
                  )}
                </div>

                <div className="flex gap-2 mt-3 pt-3" style={{ borderTop: '1px solid var(--bubble-border-subtle)' }}>
                  <BubbleButton
                    variant="primary"
                    size="sm"
                    className="flex-1"
                    onClick={() => handleTestConnection(p.provider)}
                    disabled={isTesting}
                  >
                    {isTesting ? 'Verifying...' : '⚡ Test Connection'}
                  </BubbleButton>
                  <BubbleButton
                    variant="secondary"
                    size="sm"
                    onClick={() => setConfigModalProvider(p.provider)}
                  >
                    Configure
                  </BubbleButton>
                </div>
              </BubbleCard>
            )
          })}
        </div>
      )}

      {/* ── TAB 2: Workspace & Appearance Settings ─────────────── */}
      {activeTab === 'general' && (
        <div className="g2" style={{ alignItems: 'start', gap: 20 }}>
          {/* Section 3 & 26: Appearance Bubble */}
          <BubbleCard variant="elevated" style={{ padding: 24 }}>
            <h3 className="fw-800 text-base mb-3" style={{ color: 'var(--text-primary)' }}>
              🎨 Appearance & Color System
            </h3>
            <p className="text-xs text-muted mb-4">
              Select your preferred visual style. Bubblemorphism dynamically adapts surfaces, glows, and soft glass.
            </p>

            <div className="flex gap-2 mb-4">
              {[
                { id: 'light', label: '☀️ Light Mode', desc: 'Soft off-white glass' },
                { id: 'dark',  label: '🌙 Dark Mode',  desc: 'Deep charcoal navy' },
                { id: 'system',label: '💻 System Mode',desc: 'Matches OS theme' },
              ].map(t => (
                <BubbleButton
                  key={t.id}
                  variant={theme === t.id ? 'primary' : 'secondary'}
                  size="sm"
                  className="flex-1"
                  onClick={() => setTheme(t.id as any)}
                >
                  {t.label}
                </BubbleButton>
              ))}
            </div>

            <div style={{ padding: 12, background: 'var(--bubble-bg-sunken)', borderRadius: 'var(--bubble-radius-md)', border: '1px solid var(--bubble-border-subtle)', fontSize: '0.8rem' }}>
              <span className="text-muted">Active Render Theme: </span>
              <span className="fw-700 text-brand" style={{ textTransform: 'capitalize' }}>
                {resolvedTheme} mode ({theme === 'system' ? 'synchronized with Windows' : 'forced manual'})
              </span>
            </div>
          </BubbleCard>

          {/* AI Configuration Bubble */}
          <BubbleCard variant="elevated" style={{ padding: 24 }}>
            <h3 className="fw-800 text-base mb-3" style={{ color: 'var(--text-primary)' }}>
              🤖 AI Engine Defaults
            </h3>
            <div className="flex flex-col gap-3">
              <div>
                <label className="text-xs fw-700 text-muted uppercase block mb-1">Default AI Execution Mode</label>
                <select className="select w-full">
                  <option>Auto (Smart Dynamic AI Router)</option>
                  <option>Local First (Snapdragon NPU / Ollama)</option>
                  <option>Cloud First (OpenAI / Gemini)</option>
                  <option>Hybrid (Local Knowledge + Cloud Reasoning)</option>
                  <option>Offline Only (Zero Cloud Air-Gapped)</option>
                </select>
              </div>

              <div>
                <label className="text-xs fw-700 text-muted uppercase block mb-1">ONNX Execution Provider</label>
                <select className="select w-full">
                  <option>Qualcomm QNN (Snapdragon NPU)</option>
                  <option>DirectML (DirectX 12 GPU)</option>
                  <option>CPU Reference (Fallback)</option>
                </select>
              </div>
            </div>
          </BubbleCard>

          {/* Privacy Guard Defaults Bubble */}
          <BubbleCard variant="glass" style={{ padding: 24 }}>
            <h3 className="fw-800 text-base mb-3" style={{ color: 'var(--text-primary)' }}>
              🔒 Privacy Guard Defaults
            </h3>
            <div className="flex flex-col gap-3 text-sm">
              <label className="flex justify-between items-center py-2 border-b border-subtle" style={{ cursor: 'pointer' }}>
                <span>Auto-scan prompts for sensitive credentials</span>
                <input type="checkbox" defaultChecked style={{ width: 18, height: 18, accentColor: 'var(--brand-500)' }} />
              </label>
              <label className="flex justify-between items-center py-2 border-b border-subtle" style={{ cursor: 'pointer' }}>
                <span>Block cloud when sensitive tokens detected</span>
                <input type="checkbox" defaultChecked style={{ width: 18, height: 18, accentColor: 'var(--brand-500)' }} />
              </label>
              <label className="flex justify-between items-center py-2" style={{ cursor: 'pointer' }}>
                <span>Enforce zero external telemetry</span>
                <input type="checkbox" defaultChecked style={{ width: 18, height: 18, accentColor: 'var(--brand-500)' }} />
              </label>
            </div>
          </BubbleCard>
        </div>
      )}

      {/* ── TAB 3: About System Bubble ─────────────────────────── */}
      {activeTab === 'about' && (
        <BubbleCard variant="elevated" style={{ padding: 28, maxWidth: 680 }}>
          <div className="flex items-center gap-3 mb-4">
            <div className="logo-mark" style={{ width: 44, height: 44, fontSize: 20 }}>S</div>
            <div>
              <div className="fw-800 text-lg" style={{ color: 'var(--text-primary)' }}>SnapAI Edge v1.0</div>
              <div className="text-xs text-muted">Qualcomm AI PC Challenge Edition</div>
            </div>
          </div>
          <p style={{ fontSize: '0.88rem', color: 'var(--text-secondary)', lineHeight: 1.7, marginBottom: 16 }}>
            SnapAI Edge combines on-device Snapdragon NPU acceleration, local Ollama execution, and dynamic cloud routing to provide a private, zero-latency multimodal AI assistant for HP laptops and PCs.
          </p>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, fontSize: '0.82rem' }}>
            <div style={{ padding: 10, background: 'var(--bubble-bg-sunken)', borderRadius: 'var(--bubble-radius-md)' }}>
              <span className="text-muted">Frontend:</span> React 18 · TypeScript · Vite · Bubblemorphism
            </div>
            <div style={{ padding: 10, background: 'var(--bubble-bg-sunken)', borderRadius: 'var(--bubble-radius-md)' }}>
              <span className="text-muted">Backend:</span> FastAPI · Python 3.11 · SQLite · ONNX
            </div>
          </div>
        </BubbleCard>
      )}

      {/* Configure Provider Modal Bubble */}
      <BubbleModal
        open={!!configModalProvider}
        onClose={() => setConfigModalProvider(null)}
        title={`Configure ${configModalProvider?.toUpperCase()}`}
        icon="⚙️"
      >
        <p className="text-xs text-muted mb-4">
          API keys and endpoints can be configured in your local environment file (<code>.env</code>) or saved directly below.
        </p>
        <div className="mb-4">
          <label className="text-xs fw-700 text-muted uppercase block mb-1">API Key / Token</label>
          <input className="input-field w-full" type="password" placeholder="sk-..." defaultValue="" />
        </div>
        <div className="flex justify-end gap-2 mt-4">
          <BubbleButton variant="secondary" size="sm" onClick={() => setConfigModalProvider(null)}>
            Cancel
          </BubbleButton>
          <BubbleButton variant="primary" size="sm" onClick={() => setConfigModalProvider(null)}>
            Save Configuration
          </BubbleButton>
        </div>
      </BubbleModal>
    </div>
  )
}
