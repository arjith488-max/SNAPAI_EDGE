import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useApp } from '../hooks/useAppContext'
import { hardwareAPI, benchmarkAPI, documentsAPI } from '../services/api'

import { BubbleBadge } from '../components/bubbles'

interface QuickStat { cpu_percent?: number; memory_percent?: number; memory_available_gb?: number }

const QUICK_ACTIONS = [
  { icon: '💬', label: 'Ask AI',          desc: 'Start a conversation',      to: '/chat' },
  { icon: '👁️',  label: 'Analyze Image',   desc: 'Vision AI analysis',         to: '/vision' },
  { icon: '🖥️',  label: 'Screen Copilot',  desc: 'Capture & explain screen',   to: '/screen' },
  { icon: '📄', label: 'Upload Document', desc: 'RAG-powered Q&A',            to: '/documents' },
  { icon: '🎤', label: 'Talk to AI',      desc: 'Voice assistant',            to: '/voice' },
  { icon: '🧠', label: 'Knowledge Base',  desc: 'Search your knowledge',      to: '/knowledge' },
  { icon: '📊', label: 'Benchmark',       desc: 'Measure AI performance',     to: '/benchmark' },
  { icon: '👨‍💻', label: 'Dev Copilot',     desc: 'Code assistant',             to: '/developer' },
]

export default function Dashboard() {
  const { aiMode, isOnline, ollamaAvailable, jinaConfigured, deviceInfo } = useApp()
  const [quick, setQuick] = useState<QuickStat>({})
  const [docCount, setDocCount] = useState(0)
  const [lastBench, setLastBench] = useState<{ latency_ms: number; mode: string } | null>(null)
  const navigate = useNavigate()

  useEffect(() => {
    const poll = async () => {
      try { const r = await hardwareAPI.quick(); setQuick(r.data) } catch {}
    }
    poll()
    const t = setInterval(poll, 4000)
    return () => clearInterval(t)
  }, [])

  useEffect(() => {
    documentsAPI.list().then(r => setDocCount(r.data.length)).catch(() => {})
    benchmarkAPI.results().then(r => {
      const rows = r.data as { latency_ms: number; mode: string }[]
      if (rows.length) setLastBench(rows[0])
    }).catch(() => {})
  }, [])

  const cpu    = (deviceInfo as Record<string, Record<string, unknown>>)?.cpu ?? {}
  const mem    = (deviceInfo as Record<string, Record<string, unknown>>)?.memory ?? {}
  const gpus   = (deviceInfo as Record<string, {name:string}[]>)?.gpus ?? []
  const accel  = (deviceInfo as Record<string, Record<string, unknown>>)?.ai_acceleration ?? {}
  const m      = !isOnline ? 'offline' : aiMode

  const MODE_COLOR: Record<string, string> = {
    local: 'var(--color-local)', cloud: 'var(--color-cloud)',
    hybrid: 'var(--color-hybrid)', offline: 'var(--color-offline)',
  }
  const MODE_LABEL: Record<string, string> = {
    local: 'Local AI', cloud: 'Cloud AI', hybrid: 'Hybrid AI', offline: 'Offline Mode',
  }

  return (
    <div className="page-pad">
      <div className="page-header">
        <div className="flex items-center gap-3">
          <h1 className="page-title">Dashboard</h1>
          <BubbleBadge variant={m as any}>{m.toUpperCase()}</BubbleBadge>
        </div>
        <p className="page-subtitle">System overview and quick actions</p>
      </div>

      {/* ── Top Stats ─────────────────────────────────── */}
      <div className="g4 mb-4">
        {/* AI Mode */}
        <div className="stat-card" style={{ borderColor: `${MODE_COLOR[m]}30` }}>
          <div className="stat-label">AI Mode</div>
          <div className="stat-value" style={{ fontSize: '1.1rem', color: MODE_COLOR[m] }}>{MODE_LABEL[m]}</div>
          <div className="stat-sub flex items-center gap-1 mt-2">
            <span className={`net-dot ${isOnline ? 'online' : 'offline'}`} />
            {isOnline ? 'Online' : 'Offline'}
          </div>
        </div>

        {/* Local AI */}
        <div className="stat-card">
          <div className="stat-label">Local AI</div>
          <div className="stat-value" style={{ fontSize: '0.95rem', color: ollamaAvailable ? 'var(--color-ok)' : 'var(--text-muted)' }}>
            {ollamaAvailable ? 'Ollama' : 'Not running'}
          </div>
          <div className="stat-sub" style={{ color: ollamaAvailable ? 'var(--color-ok)' : 'var(--text-muted)' }}>
            {ollamaAvailable ? '✓ LLM ready' : 'Install Ollama'}
          </div>
        </div>

        {/* Cloud AI */}
        <div className="stat-card">
          <div className="stat-label">Cloud AI</div>
          <div className="stat-value" style={{ fontSize: '0.95rem', color: jinaConfigured ? 'var(--color-cloud)' : 'var(--text-muted)' }}>
            {jinaConfigured ? 'Jina AI' : 'Not configured'}
          </div>
          <div className="stat-sub">Embeddings + Rerank</div>
        </div>

        {/* Documents */}
        <div className="stat-card">
          <div className="stat-label">Documents</div>
          <div className="stat-value">{docCount}</div>
          <div className="stat-sub">Indexed in knowledge base</div>
        </div>
      </div>

      {/* ── Device + Metrics ─────────────────────────── */}
      <div className="g2 mb-4">
        {/* Device */}
        <div className="card card-p">
          <div className="flex items-center justify-between mb-4">
            <div className="fw-600 text-base">Device</div>
            <button className="btn btn-ghost btn-xs" onClick={() => navigate('/device')}>Details →</button>
          </div>
          <div className="flex flex-col gap-3">
            {[
              ['CPU',          String(cpu.brand ?? 'Detecting...')],
              ['Architecture', String(cpu.architecture ?? 'Unknown')],
              ['Cores',        cpu.cores_physical ? `${cpu.cores_physical}P / ${cpu.cores_logical}L` : 'Unknown'],
              ['GPU',          gpus[0]?.name ?? 'Unknown'],
              ['Total RAM',    mem.total_gb ? `${mem.total_gb} GB` : 'Unknown'],
            ].map(([k, v]) => (
              <div key={k} className="flex justify-between items-center">
                <span className="text-xs text-muted">{k}</span>
                <span className="text-xs fw-500 text-secondary truncate" style={{ maxWidth: 160 }}>{v}</span>
              </div>
            ))}
          </div>

          <hr className="divider" />

          <div className="flex flex-col gap-2">
            {[
              { label: 'Snapdragon', ok: !!cpu.is_snapdragon, note: cpu.is_snapdragon ? 'Detected' : 'Not on this device' },
              { label: 'NPU',        ok: !!accel.npu_detected, note: accel.npu_detected ? 'Active' : 'Not detected' },
              { label: 'ONNX',       ok: !!accel.onnxruntime,  note: accel.onnxruntime ? `v${accel.onnxruntime_version}` : 'Not installed' },
              { label: 'DirectML',   ok: !!accel.directml,     note: accel.directml ? 'Available' : 'Not available' },
            ].map(({ label, ok, note }) => (
              <div key={label} className="flex justify-between items-center">
                <span className="text-xs text-muted">{label}</span>
                <span className="text-xs fw-500" style={{ color: ok ? 'var(--color-ok)' : 'var(--text-muted)' }}>
                  {ok ? '✓ ' : ''}{String(note)}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Live Metrics */}
        <div className="card card-p">
          <div className="flex items-center justify-between mb-4">
            <div className="fw-600 text-base">Live Metrics</div>
            <span className="text-xs text-muted">Updates every 4s</span>
          </div>

          <div className="flex flex-col gap-5">
            <div>
              <div className="flex justify-between text-xs mb-2">
                <span className="text-muted">CPU Usage</span>
                <span className="fw-600">{quick.cpu_percent?.toFixed(1) ?? '--'}%</span>
              </div>
              <div className="progress-bar" style={{ height: 6 }}>
                <div className="progress-fill" style={{ width: `${quick.cpu_percent ?? 0}%` }} />
              </div>
            </div>

            <div>
              <div className="flex justify-between text-xs mb-2">
                <span className="text-muted">Memory Usage</span>
                <span className="fw-600">{quick.memory_percent?.toFixed(1) ?? '--'}%</span>
              </div>
              <div className="progress-bar" style={{ height: 6 }}>
                <div className="progress-fill" style={{ width: `${quick.memory_percent ?? 0}%`, background: 'linear-gradient(90deg, var(--accent-purple), var(--brand-400))' }} />
              </div>
            </div>

            <div className="g2">
              <div className="card-sm">
                <div className="stat-label">Total RAM</div>
                <div style={{ fontSize: '1.2rem', fontWeight: 700, marginTop: 4 }}>
                  {mem.total_gb ? `${mem.total_gb} GB` : '--'}
                </div>
              </div>
              <div className="card-sm">
                <div className="stat-label">Free RAM</div>
                <div style={{ fontSize: '1.2rem', fontWeight: 700, color: 'var(--color-ok)', marginTop: 4 }}>
                  {quick.memory_available_gb ? `${quick.memory_available_gb.toFixed(1)} GB` : '--'}
                </div>
              </div>
            </div>

            {lastBench && (
              <div className="alert alert-success">
                <span>📊</span>
                <span>Last benchmark: <strong>{lastBench.latency_ms} ms</strong> · {lastBench.mode}</span>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* ── Quick Actions ────────────────────────────── */}
      <div className="fw-600 text-base mb-3">Quick Actions</div>
      <div className="g-auto mb-4">
        {QUICK_ACTIONS.map(a => (
          <div key={a.to} className="quick-card" onClick={() => navigate(a.to)}>
            <div className="quick-icon">{a.icon}</div>
            <div className="quick-label">{a.label}</div>
            <div className="quick-desc">{a.desc}</div>
          </div>
        ))}
      </div>

      {/* ── Edge AI Status ───────────────────────────── */}
      <div className="card card-p">
        <div className="flex items-center justify-between mb-4">
          <div className="fw-600 text-base">⚡ Snapdragon / Edge AI</div>
          <button className="btn btn-ghost btn-xs" onClick={() => navigate('/device')}>Full report →</button>
        </div>
        <div className="g3">
          {[
            { label: 'Snapdragon Processor',  ok: !!cpu.is_snapdragon,    note: cpu.is_snapdragon ? 'Detected' : 'Not on this device (x86)' },
            { label: 'ARM64 Architecture',    ok: !!cpu.is_arm64,         note: cpu.is_arm64 ? 'ARM64 (native)' : 'x86_64 (ONNX-compatible)' },
            { label: 'Qualcomm NPU',          ok: !!accel.npu_detected,   note: accel.npu_detected ? 'Active' : 'Not detected' },
            { label: 'ONNX Runtime',          ok: !!accel.onnxruntime,    note: accel.onnxruntime ? `Ready (v${accel.onnxruntime_version})` : 'Not installed' },
            { label: 'DirectML Acceleration', ok: !!accel.directml,       note: accel.directml ? 'Available' : 'Not available' },
            { label: 'QNN Runtime',           ok: false,                  note: 'Planned — needs Snapdragon X Elite' },
          ].map(item => (
            <div key={item.label} className="card-sm">
              <div className="stat-label mb-2">{item.label}</div>
              <div className="text-xs fw-500" style={{ color: item.ok ? 'var(--color-ok)' : 'var(--text-muted)' }}>
                {item.ok ? '✓ ' : 'ℹ '}{String(item.note)}
              </div>
            </div>
          ))}
        </div>
        <div className="alert alert-info mt-3">
          <span>ℹ</span>
          <span>Running on Intel i7. App is <strong>Snapdragon-ready</strong> — ONNX/DirectML/QNN inference paths are implemented and will activate automatically on Snapdragon X Elite/Plus hardware.</span>
        </div>
      </div>
    </div>
  )
}
