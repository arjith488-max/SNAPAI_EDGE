import React, { useState, useEffect, useRef, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { aiAPI, chatAPI, ModelItem } from '../services/api'
import { useApp } from '../hooks/useAppContext'
import { BubbleBadge, BubbleModal, BubbleAvatar } from '../components/bubbles'

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  mode?: string
  model?: string
  provider?: string
  latency_ms?: number
  network_used?: boolean
  local_processing?: boolean
  routing_reason?: string
  metadata?: Record<string, any>
  error?: boolean
  streaming?: boolean
}

interface Conversation {
  id: string
  title: string
  updated_at: string
}

// ── Typing Indicator Bubble ───────────────────────────────────────
function TypingIndicator({ provider }: { provider?: string }) {
  return (
    <div className="chat-message-group ai-group anim-fade">
      <BubbleAvatar type="ai" size="sm" />
      <div className="msg-body">
        <div className="msg-name">SnapAI Edge {provider ? `· ${provider}` : ''}</div>
        <div className="typing-dots" style={{ padding: '6px 0' }}>
          <span /><span /><span />
        </div>
      </div>
    </div>
  )
}

// ── Message Group with Bubblemorphism & Technical Bubble ──────────
function MessageGroup({
  msg,
  onCopy,
  onRetry,
  onSwitchToAuto,
}: {
  msg: Message
  onCopy: (t: string) => void
  onRetry: () => void
  onSwitchToAuto: () => void
}) {
  const [metaOpen, setMetaOpen] = useState(false)
  const isAI = msg.role === 'assistant'
  const isError = msg.error || msg.content.includes('request failed.')

  const modeVariant = (msg.mode?.toLowerCase() === 'local' ? 'local'
    : msg.mode?.toLowerCase() === 'cloud' ? 'cloud'
    : msg.mode?.toLowerCase() === 'hybrid' ? 'hybrid'
    : msg.mode?.toLowerCase() === 'offline' ? 'offline' : 'neutral') as any

  return (
    <div className={`chat-message-group ${isAI ? 'ai-group' : 'user-group'}`}>
      <BubbleAvatar type={isAI ? 'ai' : 'user'} size="sm" />
      <div className="msg-body">
        {isAI && (
          <div className="msg-name flex items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <span className="fw-700">SnapAI Edge</span>
              {msg.provider && (
                <span className="text-xs text-muted fw-500">
                  via <strong style={{ color: 'var(--text-primary)' }}>{msg.provider}</strong>
                </span>
              )}
            </div>
            {msg.mode && (
              <BubbleBadge variant={modeVariant} size="sm">
                {msg.mode}
              </BubbleBadge>
            )}
          </div>
        )}

        <div className="msg-content">
          {isAI ? (
            <div>
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.content}</ReactMarkdown>
              {msg.streaming && <span className="streaming-cursor">▋</span>}
            </div>
          ) : (
            <span style={{ whiteSpace: 'pre-wrap' }}>{msg.content}</span>
          )}
        </div>

        {/* Error Fallback buttons */}
        {isError && isAI && (
          <div className="mt-3 flex gap-2">
            <button className="btn btn-secondary btn-xs" onClick={onRetry}>
              🔄 Retry
            </button>
            <button className="btn btn-primary btn-xs" onClick={onSwitchToAuto}>
              🔀 Switch to Auto
            </button>
          </div>
        )}

        {/* Bubble Actions */}
        <div className="msg-actions">
          <button
            className="btn btn-ghost btn-xs"
            onClick={() => onCopy(msg.content)}
            title="Copy message"
          >
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <rect x="9" y="9" width="13" height="13" rx="2" />
              <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
            </svg>
            Copy
          </button>

          {isAI && (msg.latency_ms !== undefined || msg.provider || msg.model) && (
            <button
              className="btn btn-ghost btn-xs"
              onClick={() => setMetaOpen(p => !p)}
              style={{ color: metaOpen ? 'var(--brand-400)' : undefined }}
            >
              {metaOpen ? '▴ Hide Technical Details' : '⚡ AI Details'}
            </button>
          )}
        </div>

        {/* Collapsible Technical Details Bubble */}
        {metaOpen && isAI && (
          <div className="meta-bubble anim-slide-up">
            <div className="meta-bubble-title">
              <span>⚡ Technical Routing & Telemetry</span>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: '10px 18px' }}>
              <div>
                <span className="text-muted text-xs">Provider: </span>
                <span className="fw-600 text-xs">{msg.provider || 'Auto Router'}</span>
              </div>
              <div>
                <span className="text-muted text-xs">Model: </span>
                <span className="fw-600 text-xs">{msg.model || 'Default'}</span>
              </div>
              <div>
                <span className="text-muted text-xs">Execution Mode: </span>
                <span className="fw-600 text-xs" style={{ textTransform: 'capitalize' }}>{msg.mode || 'Local'}</span>
              </div>
              <div>
                <span className="text-muted text-xs">Latency: </span>
                <span className="fw-700 text-xs text-green">{msg.latency_ms ? `${msg.latency_ms} ms` : 'Instant'}</span>
              </div>
              <div>
                <span className="text-muted text-xs">Network: </span>
                <span className="fw-600 text-xs">{msg.network_used ? 'Cloud API' : 'Not used (Local Edge)'}</span>
              </div>
              <div>
                <span className="text-muted text-xs">Processing: </span>
                <span className="fw-600 text-xs">{msg.local_processing ? 'Snapdragon On-Device' : 'Cloud Remote'}</span>
              </div>
            </div>

            {msg.routing_reason && (
              <div style={{ marginTop: 12, paddingTop: 10, borderTop: '1px solid var(--bubble-border-subtle)' }}>
                <div style={{ fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 4, fontSize: '0.76rem' }}>
                  Why was this model selected?
                </div>
                <div style={{ whiteSpace: 'pre-line', color: 'var(--text-muted)', lineHeight: 1.5, fontSize: '0.74rem' }}>
                  {msg.routing_reason}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

// ── Main Chat Component ───────────────────────────────────────────
export default function Chat() {
  const { isOnline } = useApp()
  const navigate = useNavigate()
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [activeChatId, setActiveChatId] = useState<string | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [copied, setCopied] = useState(false)
  const [streamingEnabled, setStreamingEnabled] = useState(true)

  // Multi-model controls
  const [selectedProvider, setSelectedProvider] = useState<string>('auto')
  const [selectedMode, setSelectedMode] = useState<string>('auto')
  const [selectedModel, setSelectedModel] = useState<string>('')
  const [availableModels, setAvailableModels] = useState<ModelItem[]>([])

  // Privacy Guard State
  const [privacyModalOpen, setPrivacyModalOpen] = useState(false)
  const [pendingText, setPendingText] = useState('')
  const [privacyWarning, setPrivacyWarning] = useState<string>('')
  const [maskedPreview, setMaskedPreview] = useState<string>('')

  const endRef = useRef<HTMLDivElement>(null)
  const taRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  // Fetch conversations and models catalog
  const loadConversations = useCallback(async () => {
    try {
      const r = await chatAPI.conversations()
      setConversations(r.data)
    } catch {}
  }, [])

  const loadModels = useCallback(async () => {
    try {
      const r = await aiAPI.models()
      setAvailableModels(r.data.models || [])
    } catch {}
  }, [])

  useEffect(() => {
    loadConversations()
    loadModels()
  }, [loadConversations, loadModels])

  const loadMessages = async (id: string) => {
    try {
      const r = await chatAPI.messages(id)
      setMessages(r.data)
    } catch {}
  }

  const selectConv = (id: string) => {
    setActiveChatId(id)
    loadMessages(id)
  }

  const newChat = () => {
    setActiveChatId(null)
    setMessages([])
  }

  const deleteConv = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation()
    await chatAPI.delete(id)
    if (activeChatId === id) {
      setActiveChatId(null)
      setMessages([])
    }
    loadConversations()
  }

  // Pre-flight privacy check
  const handleSubmitPrompt = async (textToSend: string, forceAllowCloud = false) => {
    if (!textToSend.trim() || loading) return

    const isCloudPossible = selectedProvider === 'openai' || selectedProvider === 'gemini' ||
      (selectedProvider === 'auto' && selectedMode !== 'offline_only' && selectedMode !== 'local_first' && !forceAllowCloud)

    if (isCloudPossible && !forceAllowCloud) {
      try {
        const scanRes = await aiAPI.scanPrivacy(textToSend)
        if (scanRes.data.has_sensitive_data) {
          setPendingText(textToSend)
          setPrivacyWarning(scanRes.data.warning)
          setMaskedPreview(scanRes.data.masked_preview)
          setPrivacyModalOpen(true)
          return
        }
      } catch {}
    }

    executeChat(textToSend, forceAllowCloud)
  }

  // Actual execution
  const executeChat = async (textToSend: string, allowCloudOverride = false) => {
    setInput('')
    if (taRef.current) {
      taRef.current.style.height = 'auto'
    }
    setLoading(true)

    const userMsgId = Date.now().toString()
    setMessages(prev => [...prev, { id: userMsgId, role: 'user', content: textToSend }])

    const payload = {
      message: textToSend,
      conversation_id: activeChatId ?? undefined,
      provider: selectedProvider,
      mode: selectedMode,
      model: selectedModel || undefined,
      allow_cloud_override: allowCloudOverride,
    }

    if (streamingEnabled) {
      const assistantMsgId = (Date.now() + 1).toString()
      let streamContent = ''

      setMessages(prev => [
        ...prev,
        {
          id: assistantMsgId,
          role: 'assistant',
          content: '',
          provider: selectedProvider === 'auto' ? 'AI Router' : selectedProvider,
          mode: selectedMode,
          model: selectedModel,
          streaming: true,
        },
      ])

      await aiAPI.stream(
        payload,
        (token: string) => {
          streamContent += token
          setMessages(prev =>
            prev.map(m => (m.id === assistantMsgId ? { ...m, content: streamContent } : m))
          )
        },
        async () => {
          setLoading(false)
          setMessages(prev =>
            prev.map(m => (m.id === assistantMsgId ? { ...m, streaming: false } : m))
          )
          loadConversations()
        },
        (err: any) => {
          setLoading(false)
          setMessages(prev =>
            prev.map(m =>
              m.id === assistantMsgId
                ? {
                    ...m,
                    content: `${selectedProvider.toUpperCase()} request error: ${err.message}`,
                    error: true,
                    streaming: false,
                  }
                : m
            )
          )
        }
      )
    } else {
      try {
        const res = await aiAPI.chat(payload)
        const d = res.data
        if (!activeChatId && d.conversation_id) {
          setActiveChatId(d.conversation_id)
          loadConversations()
        }
        setMessages(prev => [
          ...prev,
          {
            id: d.message_id || Date.now().toString(),
            role: 'assistant',
            content: d.response || d.content,
            mode: d.mode,
            model: d.model,
            provider: d.provider,
            latency_ms: d.latency_ms,
            network_used: d.network_used,
            local_processing: d.local_processing,
            routing_reason: d.routing_reason,
            error: d.response?.includes('request failed.'),
          },
        ])
      } catch (err: any) {
        setMessages(prev => [
          ...prev,
          {
            id: Date.now().toString(),
            role: 'assistant',
            content: `❌ Request error. Provider: ${selectedProvider}. Details: ${err.message}`,
            mode: 'error',
            error: true,
          },
        ])
      } finally {
        setLoading(false)
      }
    }
  }

  const copyMsg = (text: string) => {
    navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }

  const onKey = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmitPrompt(input)
    }
  }

  const adjustTextarea = () => {
    if (!taRef.current) return
    taRef.current.style.height = 'auto'
    taRef.current.style.height = Math.min(taRef.current.scrollHeight, 220) + 'px'
  }

  const filteredModels = availableModels.filter(m =>
    selectedProvider === 'auto' ? true : m.provider === selectedProvider
  )

  const activeModelDisplay = selectedModel || (selectedProvider === 'auto' ? 'Smart Router' : 'Default Model')

  return (
    <div style={{ display: 'flex', height: 'calc(100vh - 100px)', overflow: 'hidden', position: 'relative' }}>
      {/* ── Floating Conversation History Bubble ─────────── */}
      <div className="chat-conv-panel">
        <div style={{ padding: '16px 14px 10px' }}>
          <button className="btn btn-primary w-full btn-sm" onClick={newChat}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
              <path d="M12 5v14M5 12h14" />
            </svg>
            New Conversation
          </button>
        </div>

        {/* Conversation List */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '4px 6px' }}>
          {conversations.length === 0 && (
            <div style={{ textAlign: 'center', padding: '30px 14px', color: 'var(--text-muted)' }}>
              <div style={{ fontSize: '1.8rem', opacity: 0.4, marginBottom: 6 }}>💬</div>
              <div className="text-xs">No conversations yet</div>
            </div>
          )}
          {conversations.map(c => (
            <div
              key={c.id}
              className={`conv-item${activeChatId === c.id ? ' active' : ''}`}
              onClick={() => selectConv(c.id)}
            >
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ flexShrink: 0, opacity: 0.6 }}>
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
              </svg>
              <span className="truncate flex-1" style={{ fontSize: '0.82rem' }}>{c.title}</span>
              <button
                className="btn btn-ghost btn-icon-sm"
                onClick={e => deleteConv(c.id, e)}
                style={{ width: 22, height: 22, opacity: 0.5 }}
                title="Delete chat"
              >
                <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M18 6 6 18M6 6l12 12" />
                </svg>
              </button>
            </div>
          ))}
        </div>

        {/* Live Streaming Toggle Bubble */}
        <div style={{ padding: '12px 16px', borderTop: '1px solid var(--bubble-border-subtle)', background: 'var(--bubble-bg-subtle)' }}>
          <label className="flex items-center justify-between text-xs text-muted" style={{ cursor: 'pointer' }}>
            <span className="fw-500">Live Streaming</span>
            <input
              type="checkbox"
              checked={streamingEnabled}
              onChange={e => setStreamingEnabled(e.target.checked)}
              style={{ accentColor: 'var(--brand-500)', cursor: 'pointer' }}
            />
          </label>
        </div>
      </div>

      {/* ── Chat Main Floating Workspace ─────────────────── */}
      <div className="chat-shell" style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
        {/* Top Control Bar: Floating Selectors */}
        <div
          style={{
            padding: '12px 24px',
            borderBottom: '1px solid var(--bubble-border-subtle)',
            background: 'var(--bubble-bg-subtle)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            flexWrap: 'wrap',
            gap: 12,
          }}
        >
          {/* Model Selector Bubble */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', fontWeight: 600 }}>Provider:</span>
            <select
              className="select"
              style={{ padding: '6px 30px 6px 12px', fontSize: '0.8rem' }}
              value={selectedProvider}
              onChange={e => {
                setSelectedProvider(e.target.value)
                setSelectedModel('')
              }}
            >
              <option value="auto">⚡ Auto (Smart AI Router)</option>
              <option value="openai">☁ OpenAI (Cloud)</option>
              <option value="gemini">☁ Google Gemini (Cloud)</option>
              <option value="ollama">◉ Ollama (Local)</option>
              <option value="local">⚡ Snapdragon Local</option>
            </select>

            {filteredModels.length > 0 && selectedProvider !== 'auto' && (
              <select
                className="select"
                style={{ padding: '6px 30px 6px 12px', fontSize: '0.8rem' }}
                value={selectedModel}
                onChange={e => setSelectedModel(e.target.value)}
              >
                <option value="">Default Model</option>
                {filteredModels.map(m => (
                  <option key={m.id} value={m.name}>
                    {m.name} {m.available ? '✓' : '(Not installed)'}
                  </option>
                ))}
              </select>
            )}
          </div>

          {/* Mode Selector Bubble */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', fontWeight: 600 }}>Mode:</span>
            <select
              className="select"
              style={{ padding: '6px 30px 6px 12px', fontSize: '0.8rem' }}
              value={selectedMode}
              onChange={e => setSelectedMode(e.target.value)}
            >
              <option value="auto">✨ AUTO (Dynamic)</option>
              <option value="local_first">⚡ LOCAL FIRST</option>
              <option value="cloud_first">☁ CLOUD FIRST</option>
              <option value="hybrid">◐ HYBRID</option>
              <option value="offline_only">○ OFFLINE ONLY</option>
            </select>
          </div>
        </div>

        {/* Floating Offline Mode Banner */}
        {(!isOnline || selectedMode === 'offline_only') && (
          <div
            className="anim-slide-up"
            style={{
              padding: '10px 24px',
              background: 'rgba(239, 68, 68, 0.12)',
              borderBottom: '1px solid rgba(239, 68, 68, 0.25)',
              color: '#f87171',
              fontSize: '0.82rem',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
            }}
          >
            <div className="flex items-center gap-2">
              <span className="fw-700">⚡ OFFLINE MODE</span>
              <span style={{ color: 'var(--text-secondary)' }}>
                {!isOnline ? 'Internet unavailable. Local Edge AI remains fully active.' : 'Offline-only air-gapped mode active.'}
              </span>
            </div>
            <button
              className="btn btn-ghost btn-xs"
              style={{ color: '#f87171', borderColor: 'rgba(239,68,68,0.3)' }}
              onClick={() => setSelectedMode('local_first')}
            >
              Continue Offline
            </button>
          </div>
        )}

        {/* Messages Stream */}
        <div className="chat-messages">
          {messages.length === 0 && (
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '40px 16px', gap: 20 }}>
              {/* Soft Welcome Bubble Card */}
              <div
                className="bubble-card bubble-card-elevated"
                style={{
                  maxWidth: 580,
                  width: '100%',
                  textAlign: 'center',
                  padding: '36px 30px',
                  borderRadius: 'var(--bubble-radius-xl)',
                  boxShadow: 'var(--bubble-shadow-floating)',
                }}
              >
                <div style={{ fontSize: '2.6rem', marginBottom: 12 }}>⚡</div>
                <h2 style={{ fontSize: '1.6rem', fontWeight: 800, letterSpacing: '-0.02em', color: 'var(--text-primary)' }}>
                  Welcome to SnapAI Edge
                </h2>
                <p style={{ fontSize: '0.88rem', color: 'var(--text-muted)', marginTop: 6, lineHeight: 1.6 }}>
                  Private Multimodal AI Assistant for Snapdragon PCs · Local First, Air-Gapped, & Cloud Hybrid
                </p>

                {/* Quick Action Prompt Bubbles */}
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 10, marginTop: 24 }}>
                  {[
                    { label: '⚡ Edge vs Cloud AI', prompt: 'Explain edge AI vs cloud AI tradeoffs in performance and privacy' },
                    { label: '🤖 Available Models', prompt: 'List and explain all available local and cloud models' },
                    { label: '💻 Python Quicksort', prompt: 'Write an optimized Python implementation of quicksort' },
                    { label: '🔍 Snapdragon NPU', prompt: 'How does Snapdragon NPU accelerate on-device neural models?' },
                  ].map(s => (
                    <button
                      key={s.label}
                      className="quick-action-bubble"
                      style={{ padding: '12px 16px', textAlign: 'left', borderRadius: 'var(--bubble-radius-md)' }}
                      onClick={() => handleSubmitPrompt(s.prompt)}
                    >
                      <div className="fw-700 text-sm" style={{ color: 'var(--text-primary)' }}>{s.label}</div>
                      <div className="text-xs text-muted truncate">{s.prompt}</div>
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}

          {messages.map(msg => (
            <MessageGroup
              key={msg.id}
              msg={msg}
              onCopy={copyMsg}
              onRetry={() => handleSubmitPrompt(input || 'Retry previous prompt')}
              onSwitchToAuto={() => {
                setSelectedProvider('auto')
                setSelectedMode('auto')
                handleSubmitPrompt(input || 'Retry with Auto router')
              }}
            />
          ))}

          {loading && !streamingEnabled && <TypingIndicator provider={selectedProvider} />}
          <div ref={endRef} />
        </div>

        {/* Large Floating Bubble Chat Input */}
        <div className="composer-wrap">
          <div className="bubble-composer">
            <textarea
              ref={taRef}
              className="composer-textarea"
              placeholder="Ask SnapAI Edge anything... (Shift+Enter for new line)"
              value={input}
              onChange={e => {
                setInput(e.target.value)
                adjustTextarea()
              }}
              onKeyDown={onKey}
              rows={1}
            />

            <div className="composer-footer">
              {/* Left tool shortcuts */}
              <div className="composer-tools-left">
                <button
                  type="button"
                  className="composer-tool-btn"
                  title="Upload Document"
                  onClick={() => navigate('/documents')}
                  aria-label="Upload Document"
                >
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="m21.44 11.05-9.19 9.19a6 6 0 0 1-8.49-8.49l8.57-8.57A4 4 0 1 1 17.9 8.84l-8.59 8.57a2 2 0 0 1-2.83-2.83l8.49-8.48" />
                  </svg>
                </button>
                <button
                  type="button"
                  className="composer-tool-btn"
                  title="Vision & Camera"
                  onClick={() => navigate('/vision')}
                  aria-label="Vision & Camera"
                >
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M14.5 4h-5L7 7H4a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2h-3l-2.5-3z" />
                    <circle cx="12" cy="13" r="3" />
                  </svg>
                </button>
                <button
                  type="button"
                  className="composer-tool-btn"
                  title="Voice Assistant"
                  onClick={() => navigate('/voice')}
                  aria-label="Voice Assistant"
                >
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z" />
                    <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
                    <line x1="12" x2="12" y1="19" y2="22" />
                  </svg>
                </button>

                {/* Target Model Pill Badge */}
                <BubbleBadge variant="brand" size="sm" style={{ marginLeft: 6 }}>
                  {selectedProvider === 'auto' ? '⚡ Auto' : selectedProvider.toUpperCase()} · {activeModelDisplay}
                </BubbleBadge>
              </div>

              {/* Right Send Button */}
              <div className="flex items-center gap-2">
                {copied && <span className="text-xs text-green fw-600">Copied!</span>}
                <button
                  className="send-btn"
                  onClick={() => handleSubmitPrompt(input)}
                  disabled={!input.trim() || loading}
                  title="Send Prompt (Enter)"
                  aria-label="Send Prompt"
                >
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                    <path d="M22 2 11 13" />
                    <path d="M22 2 15 22l-4-9-9-4 20-7z" />
                  </svg>
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* ── Privacy Warning Bubble Modal ─────────────────── */}
      <BubbleModal
        open={privacyModalOpen}
        onClose={() => setPrivacyModalOpen(false)}
        title="Privacy Guard Protection"
        icon="🔒"
        maxWidth={540}
      >
        <p style={{ fontSize: '0.88rem', color: 'var(--text-secondary)', lineHeight: 1.6, marginBottom: 16 }}>
          {privacyWarning || 'Sensitive tokens or credentials were detected in your prompt. How would you like to handle this request?'}
        </p>

        <div
          style={{
            background: 'var(--bubble-bg-sunken)',
            padding: '12px 16px',
            borderRadius: 'var(--bubble-radius-md)',
            fontSize: '0.82rem',
            fontFamily: 'var(--font-mono)',
            marginBottom: 22,
            border: '1px solid var(--bubble-border-subtle)',
          }}
        >
          <div style={{ color: 'var(--text-muted)', marginBottom: 6, fontSize: '0.74rem' }}>Masked Safe Preview:</div>
          <div>{maskedPreview}</div>
        </div>

        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10, justifyContent: 'flex-end' }}>
          <button
            className="btn btn-secondary btn-sm"
            onClick={() => setPrivacyModalOpen(false)}
          >
            Cancel
          </button>
          <button
            className="btn btn-secondary btn-sm"
            onClick={() => {
              setPrivacyModalOpen(false)
              executeChat(maskedPreview, false)
            }}
          >
            🎭 Mask & Send
          </button>
          <button
            className="btn btn-primary btn-sm"
            onClick={() => {
              setPrivacyModalOpen(false)
              setSelectedProvider('ollama')
              setSelectedMode('local_first')
              executeChat(pendingText, false)
            }}
          >
            ⚡ Process Locally
          </button>
          <button
            className="btn btn-danger btn-sm"
            onClick={() => {
              setPrivacyModalOpen(false)
              executeChat(pendingText, true)
            }}
          >
            ☁ Allow Cloud
          </button>
        </div>
      </BubbleModal>
    </div>
  )
}
