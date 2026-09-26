import { useState, useEffect } from 'react'
import { benchmarkAPI } from '../services/api'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts'
import { BubbleBadge, BubbleCard, BubbleButton } from '../components/bubbles'

interface BenchResult {
  id: string
  test_name: string
  model: string
  mode: string
  latency_ms: number
  memory_mb?: number
  success: boolean
  error?: string
  created_at: string
}

export default function Benchmark() {
  const [results, setResults] = useState<BenchResult[]>([])
  const [running, setRunning] = useState(false)
  const [summary, setSummary] = useState<{ tests_run: number; tests_passed: number; fastest_mode: string } | null>(null)

  useEffect(() => { load() }, [])

  const load = async () => {
    try {
      const r = await benchmarkAPI.results()
      setResults(r.data)
    } catch {}
  }

  const runBench = async () => {
    setRunning(true)
    try {
      const r = await benchmarkAPI.run()
      setSummary(r.data.summary)
      load()
    } catch (e: unknown) {
      alert(`Benchmark failed: ${e instanceof Error ? e.message : 'Unknown'}`)
    } finally {
      setRunning(false)
    }
  }

  // Prepare chart data
  const chartData = results.slice(0, 10).map(r => ({
    name: r.test_name.replace('_', ' '),
    latency: r.latency_ms,
    mode: r.mode,
  }))

  const avgLocal = results.filter(r => r.mode === 'local' && r.success).reduce((s, r, _, a) => s + r.latency_ms / a.length, 0)
  const avgCloud = results.filter(r => r.mode === 'cloud' && r.success).reduce((s, r, _, a) => s + r.latency_ms / a.length, 0)

  return (
    <div className="page-pad">
      <div className="page-header">
        <h1 className="page-title">📊 Benchmark Lab</h1>
        <p className="page-subtitle">Real On-Device Measurements · Edge Latency vs Cloud Remote Inference</p>
      </div>

      <div className="flex gap-3 mb-4 items-center flex-wrap">
        <BubbleButton
          variant="primary"
          onClick={runBench}
          disabled={running}
        >
          {running ? '⏳ Executing Benchmark Suite...' : '▶️ Run Benchmark Suite'}
        </BubbleButton>
        <span className="text-xs text-muted">
          Measures chat generation speed, token latency, and local vs cloud overhead
        </span>
      </div>

      {summary && (
        <div style={{ padding: 14, background: 'rgba(16, 185, 129, 0.12)', border: '1px solid rgba(16, 185, 129, 0.25)', borderRadius: 'var(--bubble-radius-md)', color: 'var(--color-ok)', fontSize: '0.85rem' }} className="mb-4">
          ✅ {summary.tests_passed}/{summary.tests_run} tests passed · Fastest execution mode: <strong>{summary.fastest_mode.toUpperCase()}</strong>
        </div>
      )}

      {/* Floating Performance Stat Bubbles */}
      <div className="g4 mb-4">
        <BubbleCard variant="elevated" style={{ padding: 18 }}>
          <div className="stat-label">Total Runs</div>
          <div className="stat-value">{results.length}</div>
        </BubbleCard>
        <BubbleCard variant="elevated" style={{ padding: 18 }}>
          <div className="stat-label">Avg Local Edge</div>
          <div className="stat-value" style={{ color: 'var(--color-local)' }}>
            {avgLocal ? `${avgLocal.toFixed(0)} ms` : 'N/A'}
          </div>
        </BubbleCard>
        <BubbleCard variant="elevated" style={{ padding: 18 }}>
          <div className="stat-label">Avg Cloud Remote</div>
          <div className="stat-value" style={{ color: 'var(--color-cloud)' }}>
            {avgCloud ? `${avgCloud.toFixed(0)} ms` : 'N/A'}
          </div>
        </BubbleCard>
        <BubbleCard variant="elevated" style={{ padding: 18 }}>
          <div className="stat-label">Success Rate</div>
          <div className="stat-value">
            {results.length ? `${((results.filter(r => r.success).length / results.length) * 100).toFixed(0)}%` : 'N/A'}
          </div>
        </BubbleCard>
      </div>

      {/* High-Precision Clean Chart Bubble */}
      {chartData.length > 0 && (
        <BubbleCard variant="elevated" style={{ padding: 24, marginBottom: 20 }}>
          <div className="flex justify-between items-center mb-3">
            <h3 className="fw-800 text-base" style={{ color: 'var(--text-primary)' }}>
              ⏱ Measured Response Latency (Last 10 Runs)
            </h3>
            <div className="flex gap-4 text-xs text-muted">
              <span className="flex items-center gap-1">
                <span style={{ width: 10, height: 10, borderRadius: '50%', background: '#10b981', display: 'inline-block' }} /> Local Edge
              </span>
              <span className="flex items-center gap-1">
                <span style={{ width: 10, height: 10, borderRadius: '50%', background: '#6366f1', display: 'inline-block' }} /> Cloud API
              </span>
            </div>
          </div>

          <div style={{ width: '100%', height: 260 }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData} margin={{ top: 10, right: 10, left: -10, bottom: 10 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(148, 163, 184, 0.15)" />
                <XAxis dataKey="name" tick={{ fill: 'var(--text-muted)', fontSize: 11 }} />
                <YAxis tick={{ fill: 'var(--text-muted)', fontSize: 11 }} unit=" ms" />
                <Tooltip
                  contentStyle={{
                    background: 'var(--bubble-bg-elevated)',
                    backdropFilter: 'var(--bubble-blur)',
                    border: '1px solid var(--bubble-border-highlight)',
                    borderRadius: 12,
                    color: 'var(--text-primary)',
                    boxShadow: 'var(--bubble-shadow-floating)',
                  }}
                  formatter={(v: number) => [`${v} ms`, 'Latency']}
                />
                <Bar dataKey="latency" radius={[8, 8, 0, 0]}>
                  {chartData.map((entry, i) => (
                    <Cell key={i} fill={entry.mode === 'local' ? '#10b981' : '#6366f1'} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </BubbleCard>
      )}

      {/* Results Table Bubble */}
      <BubbleCard variant="elevated" style={{ padding: 22 }}>
        <h3 className="fw-800 text-base mb-4" style={{ color: 'var(--text-primary)' }}>
          📋 Measured Telemetry Log
        </h3>
        {results.length === 0 ? (
          <div style={{ textAlign: 'center', color: 'var(--text-muted)', padding: '36px 16px' }}>
            Run a benchmark to record live performance measurements.
          </div>
        ) : (
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Test Name</th>
                  <th>Target Model</th>
                  <th>Mode</th>
                  <th>Latency</th>
                  <th>Memory</th>
                  <th>Status</th>
                  <th>Timestamp</th>
                </tr>
              </thead>
              <tbody>
                {results.map(r => (
                  <tr key={r.id}>
                    <td className="fw-600">{r.test_name}</td>
                    <td style={{ maxWidth: 160 }} className="truncate">{r.model}</td>
                    <td>
                      <BubbleBadge variant={r.mode.toLowerCase() as any} size="sm">
                        {r.mode}
                      </BubbleBadge>
                    </td>
                    <td style={{ fontWeight: 700, color: r.mode === 'local' ? 'var(--color-local)' : 'var(--color-cloud)' }}>
                      {r.latency_ms ? `${r.latency_ms} ms` : '--'}
                    </td>
                    <td>{r.memory_mb ? `${r.memory_mb} MB` : '--'}</td>
                    <td>
                      {r.success ? (
                        <span className="text-green fw-700 text-xs">✓ PASS</span>
                      ) : (
                        <span className="text-red fw-700 text-xs">✕ FAIL</span>
                      )}
                    </td>
                    <td className="text-xs text-muted">{new Date(r.created_at).toLocaleTimeString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </BubbleCard>
    </div>
  )
}
