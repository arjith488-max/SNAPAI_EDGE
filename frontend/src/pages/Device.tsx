import { useState, useEffect } from 'react'
import { hardwareAPI } from '../services/api'
import { BubbleBadge, BubbleCard, BubbleButton } from '../components/bubbles'

interface HardwareData {
  os: {
    system: string
    release: string
    version: string
    machine: string
  }
  cpu: {
    brand: string
    architecture: string
    cores_physical: number | null
    cores_logical: number | null
    frequency_mhz: number | null
    is_arm64: boolean
    is_snapdragon: boolean
  }
  memory: {
    total_gb: number | null
    available_gb: number | null
    percent_used: number | null
  }
  disk: {
    total_gb: number | null
    free_gb: number | null
  }
  gpus: Array<{ name: string; memory_mb?: number }>
  acceleration: {
    onnxruntime: boolean
    directml: boolean
    cuda: boolean
    npu_detected: boolean
    providers: string[]
  }
  network: {
    connected: boolean
  }
  ai_mode: string
  snapdragon_ready: boolean
}

export default function Device() {
  const [data, setData] = useState<HardwareData | null>(null)
  const [quickStats, setQuickStats] = useState<{ cpu_percent: number; memory_percent: number } | null>(null)
  const [loading, setLoading] = useState(true)
  const [lastRefreshed, setLastRefreshed] = useState<Date>(new Date())

  const fetchHardware = async () => {
    try {
      setLoading(true)
      const res = await hardwareAPI.info()
      setData(res.data)
      const qRes = await hardwareAPI.quick()
      setQuickStats(qRes.data)
      setLastRefreshed(new Date())
    } catch (err) {
      console.error('Failed to load device info:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchHardware()
    const timer = setInterval(async () => {
      try {
        const qRes = await hardwareAPI.quick()
        setQuickStats(qRes.data)
      } catch (e) {}
    }, 4000)
    return () => clearInterval(timer)
  }, [])

  const cpuName = data?.cpu.brand || 'Detected CPU'
  const isSnapdragon = data?.cpu.is_snapdragon
  const npuStatus = data?.acceleration.npu_detected ? 'Available' : 'Unavailable'
  const onnxStatus = data?.acceleration.onnxruntime ? 'Available' : 'Unavailable'
  const directmlStatus = data?.acceleration.directml ? 'Available' : 'Unavailable'
  const gpuName = data?.gpus && data.gpus[0]?.name ? data.gpus[0].name : 'Integrated / None'
  const ramTotal = data?.memory.total_gb ? `${data.memory.total_gb} GB` : 'Unknown'
  const ramFree = data?.memory.available_gb ? `${data.memory.available_gb} GB` : 'Unknown'

  return (
    <div className="page-pad">
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <h1 className="page-title">⚡ Snapdragon Hardware & Edge Telemetry</h1>
          <p className="page-subtitle">
            Actual detected device hardware · Qualcomm NPU status · CPU/GPU telemetry · Hardware acceleration
          </p>
        </div>
        <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
          <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
            Updated: {lastRefreshed.toLocaleTimeString()}
          </span>
          <BubbleButton variant="secondary" size="sm" onClick={fetchHardware} disabled={loading}>
            {loading ? 'Refreshing...' : '🔄 Refresh Hardware'}
          </BubbleButton>
        </div>
      </div>

      {/* Section 23: Premium Hardware Bubble */}
      <BubbleCard
        variant="elevated"
        style={{
          padding: 24,
          marginBottom: 20,
          background: 'linear-gradient(135deg, rgba(99, 102, 241, 0.12) 0%, rgba(139, 92, 246, 0.08) 100%)',
          borderColor: 'rgba(99, 102, 241, 0.25)',
        }}
      >
        <div className="flex justify-between items-center flex-wrap gap-3 mb-4">
          <div className="flex items-center gap-3">
            <div
              style={{
                width: 44,
                height: 44,
                borderRadius: 'var(--bubble-radius-md)',
                background: 'linear-gradient(135deg, #e0004d, #6366f1)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: '20px',
                color: '#fff',
                boxShadow: '0 4px 16px rgba(224, 0, 77, 0.35)',
              }}
            >
              ⚡
            </div>
            <div>
              <div className="fw-800 text-lg" style={{ color: 'var(--text-primary)' }}>
                {isSnapdragon ? 'Snapdragon AI PC' : 'Edge-Ready Host PC'}
              </div>
              <div className="text-xs text-muted">
                {isSnapdragon ? 'Native Qualcomm Snapdragon Architecture' : 'ONNX & DirectML Edge Acceleration Path'}
              </div>
            </div>
          </div>

          <div className="flex gap-2">
            <BubbleBadge variant={data?.acceleration.npu_detected ? 'local' : 'neutral'}>
              NPU: {npuStatus}
            </BubbleBadge>
            <BubbleBadge variant="brand">
              AI Acceleration: {onnxStatus === 'Available' || directmlStatus === 'Available' ? 'Available' : 'CPU Fallback'}
            </BubbleBadge>
          </div>
        </div>

        {/* Hardware Specs Grid (Actual detected values only) */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 12 }}>
          <div style={{ padding: '12px 14px', background: 'var(--bubble-bg-sunken)', borderRadius: 'var(--bubble-radius-md)', border: '1px solid var(--bubble-border-subtle)' }}>
            <div className="text-xs text-muted uppercase fw-700">CPU</div>
            <div className="fw-700 text-sm mt-1 truncate" title={cpuName}>{cpuName}</div>
            <div className="text-xs text-muted mt-1">{data?.cpu.architecture || 'Unknown'} · {data?.cpu.cores_physical ?? '--'} Cores</div>
          </div>

          <div style={{ padding: '12px 14px', background: 'var(--bubble-bg-sunken)', borderRadius: 'var(--bubble-radius-md)', border: '1px solid var(--bubble-border-subtle)' }}>
            <div className="text-xs text-muted uppercase fw-700">GPU</div>
            <div className="fw-700 text-sm mt-1 truncate" title={gpuName}>{gpuName}</div>
            <div className="text-xs text-muted mt-1">DirectML: {directmlStatus}</div>
          </div>

          <div style={{ padding: '12px 14px', background: 'var(--bubble-bg-sunken)', borderRadius: 'var(--bubble-radius-md)', border: '1px solid var(--bubble-border-subtle)' }}>
            <div className="text-xs text-muted uppercase fw-700">Qualcomm Hexagon NPU</div>
            <div className="fw-700 text-sm mt-1" style={{ color: data?.acceleration.npu_detected ? 'var(--color-ok)' : 'var(--text-secondary)' }}>
              {npuStatus}
            </div>
            <div className="text-xs text-muted mt-1">{data?.acceleration.npu_detected ? 'Dedicated Neural Processing' : 'QNN ready on Snapdragon'}</div>
          </div>

          <div style={{ padding: '12px 14px', background: 'var(--bubble-bg-sunken)', borderRadius: 'var(--bubble-radius-md)', border: '1px solid var(--bubble-border-subtle)' }}>
            <div className="text-xs text-muted uppercase fw-700">System Memory</div>
            <div className="fw-700 text-sm mt-1">{ramTotal} Total</div>
            <div className="text-xs text-green fw-600 mt-1">{ramFree} Available</div>
          </div>
        </div>
      </BubbleCard>

      {/* Live CPU & RAM Gauges */}
      <div className="g2 mb-4">
        <BubbleCard variant="elevated" style={{ padding: 22 }}>
          <div className="flex justify-between items-center mb-3">
            <span className="fw-700 text-sm">Real-Time CPU Utilization</span>
            <span className="fw-800 text-brand text-base">
              {quickStats ? `${quickStats.cpu_percent.toFixed(1)}%` : '--'}
            </span>
          </div>
          <div className="progress-bar" style={{ height: 8 }}>
            <div className="progress-fill" style={{ width: `${quickStats ? quickStats.cpu_percent : 0}%` }} />
          </div>
          <div className="flex justify-between text-xs text-muted mt-3">
            <span>Frequency: {data?.cpu.frequency_mhz ? `${(data.cpu.frequency_mhz/1000).toFixed(2)} GHz` : 'Dynamic'}</span>
            <span>OS: {data?.os.system || 'Windows'} ({data?.os.machine || 'x86_64'})</span>
          </div>
        </BubbleCard>

        <BubbleCard variant="elevated" style={{ padding: 22 }}>
          <div className="flex justify-between items-center mb-3">
            <span className="fw-700 text-sm">Real-Time Memory Utilization</span>
            <span className="fw-800 text-brand text-base">
              {quickStats ? `${quickStats.memory_percent.toFixed(1)}%` : '--'}
            </span>
          </div>
          <div className="progress-bar" style={{ height: 8 }}>
            <div
              className="progress-fill"
              style={{
                width: `${quickStats ? quickStats.memory_percent : 0}%`,
                background: 'linear-gradient(90deg, var(--accent-purple), var(--brand-400))',
              }}
            />
          </div>
          <div className="flex justify-between text-xs text-muted mt-3">
            <span>Used: {data?.memory.percent_used ?? '--'}%</span>
            <span>Available: {ramFree}</span>
          </div>
        </BubbleCard>
      </div>

      {/* Acceleration Providers Bubble */}
      <BubbleCard variant="glass" style={{ padding: 22 }}>
        <h3 className="fw-800 text-base mb-3" style={{ color: 'var(--text-primary)' }}>
          ONNX & Hardware Acceleration Providers
        </h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 10 }}>
          {[
            { name: 'Qualcomm NPU (QNN)', status: data?.acceleration.npu_detected ? 'Available' : 'Unavailable', note: 'Native Snapdragon X Elite/Plus' },
            { name: 'DirectML (DirectX 12)', status: directmlStatus, note: 'GPU/APU Acceleration for Windows' },
            { name: 'ONNX Runtime', status: onnxStatus, note: 'Edge Neural Execution Framework' },
            { name: 'CPU Reference Provider', status: 'Available', note: 'High-Precision Fallback' },
          ].map(p => (
            <div key={p.name} style={{ padding: '12px 14px', background: 'var(--bubble-bg-sunken)', borderRadius: 'var(--bubble-radius-md)', border: '1px solid var(--bubble-border-subtle)' }}>
              <div className="flex justify-between items-center">
                <span className="fw-700 text-xs">{p.name}</span>
                <span className="text-xs fw-600" style={{ color: p.status === 'Available' ? 'var(--color-ok)' : 'var(--text-muted)' }}>
                  {p.status}
                </span>
              </div>
              <div className="text-xs text-muted mt-1">{p.note}</div>
            </div>
          ))}
        </div>
      </BubbleCard>
    </div>
  )
}
