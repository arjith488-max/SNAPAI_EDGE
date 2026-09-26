import { useApp } from '../hooks/useAppContext'
import { useEffect, useState } from 'react'
import { hardwareAPI } from '../services/api'
import { useNavigate, useLocation } from 'react-router-dom'
import { BubbleBadge } from './bubbles'

interface QuickStat {
  cpu_percent?: number
  memory_percent?: number
  memory_available_gb?: number
}

const MODE_COLOR: Record<string, string> = {
  local: 'var(--color-local)',
  cloud: 'var(--color-cloud)',
  hybrid: 'var(--color-hybrid)',
  offline: 'var(--color-offline)',
}

export default function ContextPanel() {
  const { aiMode, isOnline, ollamaAvailable, jinaConfigured, deviceInfo } = useApp()
  const [quick, setQuick] = useState<QuickStat>({})
  const navigate = useNavigate()
  const location = useLocation()

  useEffect(() => {
    const poll = async () => {
      try {
        const r = await hardwareAPI.quick()
        setQuick(r.data)
      } catch {}
    }
    poll()
    const t = setInterval(poll, 4000)
    return () => clearInterval(t)
  }, [])

  const m = !isOnline ? 'offline' : aiMode
  const cpu = (deviceInfo as Record<string, Record<string, unknown>>)?.cpu ?? {}
  const accel = (deviceInfo as Record<string, Record<string, unknown>>)?.ai_acceleration ?? {}

  return (
    <>
      <div className="context-header">
        <span className="text-xs fw-700 text-muted" style={{ letterSpacing: '0.08em', textTransform: 'uppercase' }}>
          Live Context
        </span>
        <BubbleBadge variant="neutral" size="sm">
          {location.pathname.replace('/', '') || 'dashboard'}
        </BubbleBadge>
      </div>

      {/* AI Mode Bubble */}
      <div className="context-section">
        <div className="context-label">AI Engine Status</div>
        <div className="flex items-center gap-2 mb-3">
          <div
            className="bubble-dot"
            style={{
              background: MODE_COLOR[m] || 'var(--color-local)',
              boxShadow: `0 0 8px ${MODE_COLOR[m] || 'var(--color-local)'}`,
            }}
          />
          <span className="fw-800" style={{ fontSize: '0.9rem', color: MODE_COLOR[m] || 'var(--color-local)' }}>
            {m.toUpperCase()} MODE
          </span>
        </div>
        <div className="flex flex-col gap-2">
          <div className="flex justify-between text-xs">
            <span className="text-muted">Internet Connectivity</span>
            <span style={{ color: isOnline ? 'var(--color-ok)' : 'var(--color-error)', fontWeight: 600 }}>
              {isOnline ? '● Online' : '● Offline'}
            </span>
          </div>
          <div className="flex justify-between text-xs">
            <span className="text-muted">Local Ollama LLM</span>
            <span style={{ color: ollamaAvailable ? 'var(--color-ok)' : 'var(--text-muted)', fontWeight: 600 }}>
              {ollamaAvailable ? '● Ready' : '○ Not running'}
            </span>
          </div>
          <div className="flex justify-between text-xs">
            <span className="text-muted">Jina Embeddings</span>
            <span style={{ color: jinaConfigured ? 'var(--color-ok)' : 'var(--text-muted)', fontWeight: 600 }}>
              {jinaConfigured ? '● Active' : '○ No Key'}
            </span>
          </div>
        </div>
      </div>

      {/* Live Telemetry Progress */}
      <div className="context-section">
        <div className="context-label">Live Telemetry</div>
        <div className="flex flex-col gap-3">
          <div>
            <div className="flex justify-between text-xs mb-1">
              <span className="text-muted">CPU Load</span>
              <span className="fw-700">{quick.cpu_percent?.toFixed(0) ?? '--'}%</span>
            </div>
            <div className="progress-bar">
              <div className="progress-fill" style={{ width: `${quick.cpu_percent ?? 0}%` }} />
            </div>
          </div>
          <div>
            <div className="flex justify-between text-xs mb-1">
              <span className="text-muted">Memory Load</span>
              <span className="fw-700">{quick.memory_percent?.toFixed(0) ?? '--'}%</span>
            </div>
            <div className="progress-bar">
              <div
                className="progress-fill"
                style={{
                  width: `${quick.memory_percent ?? 0}%`,
                  background: 'linear-gradient(90deg, var(--accent-purple), var(--brand-400))',
                }}
              />
            </div>
          </div>
          {quick.memory_available_gb && (
            <div className="flex justify-between text-xs">
              <span className="text-muted">Free RAM</span>
              <span className="fw-700 text-green">{quick.memory_available_gb.toFixed(1)} GB</span>
            </div>
          )}
        </div>
      </div>

      {/* Hardware Status */}
      <div className="context-section">
        <div className="context-label">Hardware Acceleration</div>
        <div className="flex flex-col gap-2 text-xs">
          {[
            ['Snapdragon', cpu.is_snapdragon ? '✓ Detected' : 'Host PC (x86)'],
            ['NPU', accel.npu_detected ? '✓ Hexagon Active' : 'DirectML Accelerated'],
            ['ONNX', accel.onnxruntime ? `✓ v${accel.onnxruntime_version}` : '○ Not installed'],
            ['DirectML', accel.directml ? '✓ Available' : '○ Fallback'],
          ].map(([k, v]) => (
            <div key={k} className="flex justify-between">
              <span className="text-muted">{k}</span>
              <span className="fw-600" style={{ color: String(v).startsWith('✓') ? 'var(--color-ok)' : 'var(--text-secondary)' }}>
                {v}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Quick Navigation Bubbles */}
      <div className="context-section">
        <div className="context-label">Quick Links</div>
        <div className="flex flex-col gap-1">
          {[
            { label: '🔀 AI Router Flow', path: '/router' },
            { label: '📊 Benchmark Lab', path: '/benchmark' },
            { label: '🔒 Privacy Guard', path: '/privacy' },
            { label: '🖥️ Hardware Monitor', path: '/device' },
          ].map(a => (
            <button
              key={a.path}
              className="btn btn-ghost btn-sm w-full"
              style={{ justifyContent: 'flex-start', fontSize: '0.8rem', padding: '7px 10px' }}
              onClick={() => navigate(a.path)}
            >
              {a.label}
            </button>
          ))}
        </div>
      </div>

      {/* Edge Architecture Note */}
      <div className="context-section" style={{ borderBottom: 'none' }}>
        <div style={{ padding: '10px 12px', background: 'var(--bubble-bg-subtle)', borderRadius: 'var(--bubble-radius-md)', border: '1px solid var(--bubble-border-subtle)', fontSize: '0.74rem', color: 'var(--text-muted)' }}>
          <span>⚡ </span>
          <span>SnapAI Edge activates Qualcomm QNN and DirectML paths on Snapdragon PCs.</span>
        </div>
      </div>
    </>
  )
}
