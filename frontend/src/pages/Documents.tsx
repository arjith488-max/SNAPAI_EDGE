import { useState, useEffect, useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import { useNavigate } from 'react-router-dom'
import { documentsAPI, ragAPI } from '../services/api'
import { BubbleBadge, BubbleCard, BubbleButton } from '../components/bubbles'

interface Doc {
  id: string
  filename: string
  file_type: string
  size_bytes: number
  pages?: number
  chars?: number
  chunks?: number
  collection: string
  index_status: string
}

interface RAGResult {
  answer: string
  sources: { filename: string; chunk: number; score: number }[]
  mode?: string
  latency_ms?: number
}

export default function Documents() {
  const [docs, setDocs] = useState<Doc[]>([])
  const [uploading, setUploading] = useState(false)
  const [indexing, setIndexing] = useState<string | null>(null)
  const [query, setQuery] = useState('')
  const [ragResult, setRagResult] = useState<RAGResult | null>(null)
  const [querying, setQuerying] = useState(false)
  const [selectedDocs, setSelectedDocs] = useState<string[]>([])
  const navigate = useNavigate()

  const loadDocs = useCallback(async () => {
    try {
      const r = await documentsAPI.list()
      setDocs(r.data)
    } catch {}
  }, [])

  useEffect(() => { loadDocs() }, [loadDocs])

  const onDrop = useCallback(async (accepted: File[]) => {
    setUploading(true)
    for (const f of accepted) {
      try {
        await documentsAPI.upload(f)
      } catch (e: unknown) {
        const msg = e instanceof Error ? e.message : 'Unknown'
        alert(`Upload failed for ${f.name}: ${msg}`)
      }
    }
    setUploading(false)
    loadDocs()
  }, [loadDocs])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'text/plain': ['.txt'],
      'text/markdown': ['.md'],
      'text/csv': ['.csv'],
      'application/json': ['.json'],
    },
    multiple: true,
  })

  const indexDoc = async (docId: string) => {
    setIndexing(docId)
    try {
      await ragAPI.index(docId)
      loadDocs()
    } catch (e: unknown) {
      alert(`Indexing failed: ${e instanceof Error ? e.message : 'Unknown error'}`)
    } finally {
      setIndexing(null)
    }
  }

  const deleteDoc = async (docId: string) => {
    if (!confirm('Delete this document and its local index?')) return
    await documentsAPI.delete(docId)
    setSelectedDocs(prev => prev.filter(id => id !== docId))
    loadDocs()
  }

  const runQuery = async () => {
    if (!query.trim()) return
    setQuerying(true)
    setRagResult(null)
    try {
      const r = await ragAPI.query(query, 'snapai_docs', 5, selectedDocs.length ? selectedDocs : undefined)
      setRagResult(r.data)
    } catch (e: unknown) {
      setRagResult({ answer: `Query failed: ${e instanceof Error ? e.message : 'Unknown'}`, sources: [] })
    } finally {
      setQuerying(false)
    }
  }

  const toggleSelect = (id: string) => {
    setSelectedDocs(prev => prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id])
  }

  const fmt = (bytes: number) => bytes > 1e6 ? `${(bytes/1e6).toFixed(1)} MB` : `${(bytes/1024).toFixed(0)} KB`

  return (
    <div className="page-pad">
      <div className="page-header">
        <h1 className="page-title">📄 Document Intelligence & RAG</h1>
        <p className="page-subtitle">Local On-Device Knowledge Retrieval · Semantic Embeddings · Private Vector Indexing</p>
      </div>

      <div className="g2" style={{ alignItems: 'start', gap: 20 }}>
        {/* Left: Upload Zone & Document Bubbles */}
        <div className="flex flex-col gap-4">
          {/* Rounded Dropzone Bubble */}
          <div {...getRootProps()} className={`dropzone ${isDragActive ? 'dragging' : ''}`}>
            <input {...getInputProps()} />
            <div style={{ fontSize: '2.5rem', marginBottom: 10, opacity: 0.6 }}>📂</div>
            <div className="dropzone-text">
              <strong style={{ fontSize: '0.95rem' }}>Drop research papers or files here</strong>
              <div style={{ marginTop: 4, fontSize: '0.78rem' }}>
                PDF, TXT, Markdown, CSV, JSON — processed completely on-device
              </div>
            </div>
          </div>

          {uploading && (
            <div style={{ padding: 12, background: 'rgba(99, 102, 241, 0.1)', color: 'var(--brand-400)', borderRadius: 'var(--bubble-radius-md)', fontSize: '0.84rem' }} className="flex items-center gap-2">
              <div className="typing-dots"><span /><span /><span /></div>
              <span>Uploading and extracting text...</span>
            </div>
          )}

          {/* Floating Document Bubbles Container */}
          <BubbleCard variant="elevated" style={{ padding: 22 }}>
            <div className="flex justify-between items-center mb-4">
              <h3 className="fw-800 text-base" style={{ color: 'var(--text-primary)' }}>
                Indexed Documents ({docs.length})
              </h3>
              {selectedDocs.length > 0 && (
                <BubbleBadge variant="brand">
                  {selectedDocs.length} selected for query
                </BubbleBadge>
              )}
            </div>

            {docs.length === 0 ? (
              <div style={{ textAlign: 'center', color: 'var(--text-muted)', padding: '40px 16px' }}>
                <div style={{ fontSize: '2rem', opacity: 0.3, marginBottom: 8 }}>📄</div>
                <div className="text-xs">No documents uploaded yet. Upload a PDF or file to build your knowledge base.</div>
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                {docs.map(doc => {
                  const isSelected = selectedDocs.includes(doc.id)
                  const isIndexed = doc.index_status === 'ready'
                  return (
                    <div
                      key={doc.id}
                      onClick={() => toggleSelect(doc.id)}
                      className={`bubble-card bubble-card-interactive ${isSelected ? 'bubble-card-elevated' : 'bubble-card-subtle'}`}
                      style={{
                        padding: '14px 16px',
                        cursor: 'pointer',
                        borderColor: isSelected ? 'var(--brand-500)' : undefined,
                      }}
                    >
                      <div className="flex justify-between items-start gap-3">
                        <div className="flex items-start gap-3" style={{ minWidth: 0, flex: 1 }}>
                          <span style={{ fontSize: '1.4rem' }}>
                            {doc.file_type === 'pdf' ? '📕' : '📝'}
                          </span>
                          <div style={{ minWidth: 0, flex: 1 }}>
                            <div className="fw-700 text-sm truncate" style={{ color: 'var(--text-primary)' }}>
                              {doc.filename}
                            </div>
                            <div className="text-xs text-muted mt-1">
                              {fmt(doc.size_bytes)}
                              {doc.pages ? ` · ${doc.pages} pages` : ''}
                              {doc.chunks ? ` · ${doc.chunks} chunks` : ''}
                            </div>
                          </div>
                        </div>

                        {/* Status & Actions */}
                        <div className="flex items-center gap-2" style={{ flexShrink: 0 }}>
                          <BubbleBadge variant={isIndexed ? 'local' : 'warning'} size="sm">
                            {doc.index_status}
                          </BubbleBadge>

                          {!isIndexed && (
                            <BubbleButton
                              variant="primary"
                              size="xs"
                              onClick={e => { e.stopPropagation(); indexDoc(doc.id) }}
                              disabled={indexing === doc.id}
                            >
                              {indexing === doc.id ? '⏳' : '⚡ Index'}
                            </BubbleButton>
                          )}

                          <BubbleButton
                            variant="ghost"
                            size="xs"
                            onClick={e => { e.stopPropagation(); deleteDoc(doc.id) }}
                            title="Delete"
                          >
                            🗑
                          </BubbleButton>
                        </div>
                      </div>
                    </div>
                  )
                })}
              </div>
            )}
          </BubbleCard>
        </div>

        {/* Right: RAG Query & Answers Bubble */}
        <div className="flex flex-col gap-4">
          <BubbleCard variant="elevated" style={{ padding: 24 }}>
            <h3 className="fw-800 text-base mb-3" style={{ color: 'var(--text-primary)' }}>
              Ask Questions to Documents
            </h3>
            <p className="text-xs text-muted mb-4">
              Query across all indexed documents or specific selected files using local embeddings and RAG reasoning.
            </p>

            <div className="flex gap-2 mb-3">
              <input
                className="input-field flex-1"
                placeholder="Ask anything about the uploaded documents..."
                value={query}
                onChange={e => setQuery(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && runQuery()}
              />
              <BubbleButton
                variant="primary"
                onClick={runQuery}
                disabled={!query.trim() || querying}
              >
                {querying ? '⏳' : '🔍 Query'}
              </BubbleButton>
            </div>

            {querying && (
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '40px 10px', gap: 10 }}>
                <div className="typing-dots"><span /><span /><span /></div>
                <div className="text-xs text-muted">Searching semantic vector index...</div>
              </div>
            )}

            {ragResult && !querying && (
              <div className="anim-slide-up mt-3">
                <div style={{ padding: 18, background: 'var(--bubble-bg-sunken)', borderRadius: 'var(--bubble-radius-md)', border: '1px solid var(--bubble-border-subtle)' }}>
                  <div className="flex justify-between items-center mb-2">
                    <div className="fw-700 text-xs text-brand">RAG Intelligence Answer</div>
                    {ragResult.latency_ms && (
                      <span className="text-xs text-green fw-600">⏱ {ragResult.latency_ms} ms</span>
                    )}
                  </div>
                  <div style={{ fontSize: '0.92rem', lineHeight: 1.7, color: 'var(--text-secondary)', whiteSpace: 'pre-wrap' }}>
                    {ragResult.answer}
                  </div>
                </div>

                {ragResult.sources && ragResult.sources.length > 0 && (
                  <div className="mt-4">
                    <div className="text-xs fw-700 text-muted uppercase mb-2">Cited Document Passages</div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                      {ragResult.sources.map((src, i) => (
                        <div
                          key={i}
                          style={{
                            padding: '8px 12px',
                            background: 'var(--bubble-bg-subtle)',
                            borderRadius: 'var(--bubble-radius-sm)',
                            border: '1px solid var(--bubble-border-subtle)',
                            fontSize: '0.78rem',
                          }}
                          className="flex justify-between items-center"
                        >
                          <span className="truncate fw-500" style={{ maxWidth: '80%' }}>📄 {src.filename}</span>
                          <span className="text-muted text-xs">Score: {(src.score * 100).toFixed(0)}%</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                <div className="mt-4 flex gap-2">
                  <BubbleButton
                    variant="secondary"
                    size="sm"
                    onClick={() => navigate('/chat')}
                  >
                    💬 Discuss in Chat
                  </BubbleButton>
                </div>
              </div>
            )}
          </BubbleCard>
        </div>
      </div>
    </div>
  )
}
