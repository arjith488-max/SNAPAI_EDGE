import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { modelsAPI } from '../services/api'
import { BubbleBadge, BubbleCard, BubbleButton } from '../components/bubbles'

interface Model {
  id: string
  name: string
  type: string
  size_mb?: number
  source: string
  runtime: string
  status: string
  local: boolean
  provider: string
  task: string
  license: string
  quantization?: string
  install_cmd?: string
  hub_url?: string
  snapdragon_optimized?: boolean
  latency_note?: string
  ollama_installed?: boolean
}

export default function Models() {
  const [models, setModels] = useState<Model[]>([])
  const [meta, setMeta] = useState<{ ollama_running: boolean; jina_configured: boolean; openai_configured: boolean } | null>(null)
  const [filter, setFilter] = useState<'all' | 'local' | 'cloud'>('all')
  const navigate = useNavigate()

  useEffect(() => { load() }, [])

  const load = async () => {
    try {
      const r = await modelsAPI.list()
      setModels(r.data.models)
      setMeta({ ollama_running: r.data.ollama_running, jina_configured: r.data.jina_configured, openai_configured: r.data.openai_configured })
    } catch {}
  }

  const filtered = models.filter(m => filter === 'all' ? true : filter === 'local' ? m.local : !m.local)

  return (
    <div className="page-pad">
      <div className="page-header">
        <h1 className="page-title">🤖 Model Fleet Management</h1>
        <p className="page-subtitle">On-Device Snapdragon Models · Local LLMs · Cloud Intelligence · Qualcomm AI Hub</p>
      </div>

      {/* Meta Provider Status Bubbles */}
      {meta && (
        <div className="g3 mb-4">
          <BubbleCard variant="elevated" style={{ padding: 18 }}>
            <div className="stat-label">Local LLM Engine</div>
            <div className="flex items-center gap-2 mt-1">
              <span className={`net-dot ${meta.ollama_running ? 'online' : 'offline'}`} />
              <span className="fw-700 text-base" style={{ color: meta.ollama_running ? 'var(--color-ok)' : 'var(--color-error)' }}>
                {meta.ollama_running ? 'Ollama Active' : 'Not Running'}
              </span>
            </div>
            <div className="text-xs text-muted mt-2">
              {meta.ollama_running ? 'Ready for zero-latency local inference' : 'Install from ollama.com to enable edge AI'}
            </div>
          </BubbleCard>

          <BubbleCard variant="elevated" style={{ padding: 18 }}>
            <div className="stat-label">Embedding Engine</div>
            <div className="flex items-center gap-2 mt-1">
              <span className={`net-dot ${meta.jina_configured ? 'online' : 'offline'}`} />
              <span className="fw-700 text-base" style={{ color: meta.jina_configured ? 'var(--color-ok)' : 'var(--color-warn)' }}>
                {meta.jina_configured ? 'Jina AI Active' : 'No API Key'}
              </span>
            </div>
            <div className="text-xs text-muted mt-2">
              Semantic embeddings & document reranking
            </div>
          </BubbleCard>

          <BubbleCard variant="elevated" style={{ padding: 18 }}>
            <div className="stat-label">Cloud Fallback</div>
            <div className="flex items-center gap-2 mt-1">
              <span className={`net-dot ${meta.openai_configured ? 'online' : 'offline'}`} />
              <span className="fw-700 text-base" style={{ color: meta.openai_configured ? 'var(--color-ok)' : 'var(--text-muted)' }}>
                {meta.openai_configured ? 'Cloud Ready' : 'Unconfigured'}
              </span>
            </div>
            <div className="text-xs text-muted mt-2">
              Complex reasoning fallback when permitted
            </div>
          </BubbleCard>
        </div>
      )}

      {/* Filter Tabs as Soft Bubbles */}
      <div className="flex gap-2 mb-4">
        {(['all', 'local', 'cloud'] as const).map(f => (
          <BubbleButton
            key={f}
            variant={filter === f ? 'primary' : 'secondary'}
            size="sm"
            pill
            onClick={() => setFilter(f)}
          >
            {f === 'all' ? 'All Models' : f === 'local' ? '⚡ Local Edge' : '☁️ Cloud Remote'}
          </BubbleButton>
        ))}
      </div>

      {/* Floating Model Bubbles */}
      <div style={{ display: 'grid', gap: 14 }}>
        {filtered.map(model => {
          const isReady = model.status === 'ready'
          return (
            <BubbleCard
              key={model.id}
              variant="elevated"
              style={{ padding: '20px 24px', display: 'flex', gap: 18, alignItems: 'flex-start' }}
            >
              <div style={{ fontSize: '2.4rem', flexShrink: 0 }}>
                {model.type === 'llm' ? '🧠' : model.type === 'vision_llm' ? '👁️' : model.type === 'speech' ? '🎤' : model.type === 'embedding' ? '🔢' : '🤖'}
              </div>

              <div style={{ flex: 1, minWidth: 0 }}>
                <div className="flex justify-between items-center flex-wrap gap-2 mb-1">
                  <div className="flex items-center gap-2">
                    <h3 className="fw-800 text-base" style={{ color: 'var(--text-primary)', margin: 0 }}>
                      {model.name}
                    </h3>
                    {model.snapdragon_optimized && (
                      <BubbleBadge variant="brand" size="sm">
                        ⚡ Snapdragon NPU
                      </BubbleBadge>
                    )}
                  </div>
                  <BubbleBadge variant={isReady ? 'local' : 'neutral'} size="sm">
                    {model.status.replace('_', ' ').toUpperCase()}
                  </BubbleBadge>
                </div>

                <p style={{ fontSize: '0.84rem', color: 'var(--text-secondary)', margin: '4px 0 10px' }}>
                  {model.task}
                </p>

                <div className="flex flex-wrap gap-2 mb-3">
                  <span className="bubble-badge bubble-badge-neutral">{model.local ? '⚡ Local' : '☁ Cloud'}</span>
                  <span className="bubble-badge bubble-badge-neutral">{model.runtime}</span>
                  {model.size_mb && (
                    <span className="bubble-badge bubble-badge-neutral">
                      {model.size_mb >= 1000 ? `${(model.size_mb/1000).toFixed(1)} GB` : `${model.size_mb} MB`}
                    </span>
                  )}
                  {model.quantization && <span className="bubble-badge bubble-badge-neutral">{model.quantization}</span>}
                  <span className="bubble-badge bubble-badge-neutral">{model.provider}</span>
                </div>

                {model.install_cmd && (
                  <div style={{ marginTop: 8 }}>
                    <code style={{ fontSize: '0.8rem', background: 'var(--bubble-bg-sunken)', padding: '5px 12px', borderRadius: 'var(--bubble-radius-xs)', border: '1px solid var(--bubble-border-subtle)' }}>
                      {model.install_cmd}
                    </code>
                  </div>
                )}

                {/* Floating Action Buttons */}
                <div className="flex items-center gap-2 mt-4">
                  <BubbleButton
                    variant="primary"
                    size="xs"
                    onClick={() => navigate('/chat')}
                  >
                    💬 Use in Chat
                  </BubbleButton>

                  <BubbleButton
                    variant="secondary"
                    size="xs"
                    onClick={() => navigate('/benchmark')}
                  >
                    📊 Benchmark
                  </BubbleButton>

                  {model.hub_url && (
                    <a
                      href={model.hub_url}
                      target="_blank"
                      rel="noreferrer"
                      className="btn btn-ghost btn-xs"
                      style={{ color: 'var(--brand-400)' }}
                    >
                      🔗 Qualcomm AI Hub →
                    </a>
                  )}
                </div>
              </div>
            </BubbleCard>
          )
        })}
      </div>
    </div>
  )
}
