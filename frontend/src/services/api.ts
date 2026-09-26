import axios from 'axios'

const BASE = '/api'

const api = axios.create({ baseURL: BASE, timeout: 120000 })

// ─── Unified AI API ────────────────────────────────────────────────
export interface UnifiedChatPayload {
  messages?: Array<{ role: string; content: string; attachments?: unknown[] }>
  message?: string
  provider?: string
  mode?: string
  model?: string
  conversation_id?: string
  prefer_local?: boolean
  allow_cloud_override?: boolean
  attachments?: unknown[]
}

export interface ModelItem {
  id: string
  provider: string
  name: string
  location: string
  capabilities: string[]
  streaming: boolean
  vision: boolean
  embedding: boolean
  available: boolean
  description?: string
  quantization?: string
  size_mb?: number
  hardware_accelerated?: boolean
}

export interface ProviderItem {
  provider: string
  name: string
  type: string
  available: boolean
  configured: boolean
  status_text: string
  models_count: number
  active_model?: string
  endpoint?: string
  hardware_status?: string
  latency_ms?: number
  error?: string
}

export const aiAPI = {
  chat: (payload: UnifiedChatPayload) => api.post('/ai/chat', payload),
  
  stream: async (
    payload: UnifiedChatPayload,
    onToken: (token: string) => void,
    onDone: (data?: any) => void,
    onError: (err: any) => void
  ) => {
    try {
      const response = await fetch(`${BASE}/ai/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      if (!response.ok) {
        throw new Error(`Streaming failed with status: ${response.status}`)
      }
      const reader = response.body?.getReader()
      const decoder = new TextDecoder()
      if (!reader) throw new Error('No readable stream')

      let buffer = ''
      while (true) {
        const { value, done } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          const trimmed = line.trim()
          if (trimmed.startsWith('data:')) {
            try {
              const data = JSON.parse(trimmed.slice(5).trim())
              if (data.token) onToken(data.token)
              if (data.done) {
                onDone(data)
                return
              }
              if (data.error) {
                onError(new Error(data.error))
                return
              }
            } catch {
              // ignore malformed SSE line
            }
          }
        }
      }
      onDone()
    } catch (e) {
      onError(e)
    }
  },

  providers: () => api.get<{ providers: ProviderItem[] }>('/ai/providers'),
  models: (params?: { provider?: string; location?: string; available_only?: boolean }) =>
    api.get<{ models: ModelItem[] }>('/ai/models', { params }),
  route: (payload: Partial<UnifiedChatPayload>) => api.post('/ai/route', payload),
  health: () => api.post('/ai/health'),
  testProvider: (provider: string, prompt?: string) =>
    api.post('/ai/provider/test', { provider, prompt }),
  status: () => api.get('/ai/status'),
  scanPrivacy: (text: string) => api.post('/ai/privacy/scan', { text }),
}

// ─── Chat (Legacy / Compatibility) ──────────────────────────────────
export const chatAPI = {
  send: (message: string, conversationId?: string, preferLocal = false, attachments?: unknown[]) =>
    api.post('/ai/chat', { message, conversation_id: conversationId, prefer_local: preferLocal, attachments }),
  conversations: () => api.get('/ai/conversations'),
  messages: (id: string) => api.get(`/ai/conversations/${id}/messages`),
  delete: (id: string) => api.delete(`/ai/conversations/${id}`),
  rename: (id: string, title: string) => api.patch(`/ai/conversations/${id}`, { title }),
  routeInfo: () => api.get('/ai/route'),
}

// ─── Documents ────────────────────────────────────────────────────
export const documentsAPI = {
  upload: (file: File, collection = 'default') => {
    const form = new FormData()
    form.append('file', file)
    form.append('collection', collection)
    return api.post('/documents/upload', form, { headers: { 'Content-Type': 'multipart/form-data' } })
  },
  list: (collection?: string) => api.get('/documents', { params: collection ? { collection } : {} }),
  delete: (id: string) => api.delete(`/documents/${id}`),
  preview: (id: string) => api.get(`/documents/${id}/preview`),
}

// ─── RAG ──────────────────────────────────────────────────────────
export const ragAPI = {
  index: (docId: string, collection = 'snapai_docs') =>
    api.post('/rag/index', { doc_id: docId, collection }),
  query: (query: string, collection = 'snapai_docs', topK = 5, docIds?: string[]) =>
    api.post('/rag/query', { query, collection, top_k: topK, doc_ids: docIds }),
  collections: () => api.get('/rag/collections'),
  deleteIndex: (docId: string) => api.delete(`/rag/index/${docId}`),
}

// ─── Vision ───────────────────────────────────────────────────────
export const visionAPI = {
  analyze: (file: File, prompt: string, task = 'describe', preferLocal = false) => {
    const form = new FormData()
    form.append('file', file)
    form.append('prompt', prompt)
    form.append('task', task)
    form.append('prefer_local', String(preferLocal))
    return api.post('/ai/vision', form, { headers: { 'Content-Type': 'multipart/form-data' } })
  },
}

// ─── Voice ────────────────────────────────────────────────────────
export const voiceAPI = {
  transcribe: (file: File, language = 'en') => {
    const form = new FormData()
    form.append('file', file)
    form.append('language', language)
    return api.post('/ai/transcribe', form, { headers: { 'Content-Type': 'multipart/form-data' } })
  },
  speak: (text: string, voice = 'alloy') =>
    api.post('/ai/speak', { text, voice }, { responseType: 'blob' }),
}

// ─── Hardware ─────────────────────────────────────────────────────
export const hardwareAPI = {
  info: () => api.get('/device/info'),
  quick: () => api.get('/device/quick'),
}

// ─── Models ───────────────────────────────────────────────────────
export const modelsAPI = {
  list: () => api.get('/models'),
  get: (id: string) => api.get(`/models/${id}`),
}

// ─── Benchmark ────────────────────────────────────────────────────
export const benchmarkAPI = {
  run: () => api.post('/benchmark/run'),
  results: () => api.get('/benchmark/results'),
}

// ─── Privacy ──────────────────────────────────────────────────────
export const privacyAPI = {
  status: () => api.get('/privacy/status'),
  update: (settings: { privacy_mode: string; cloud_enabled: boolean; telemetry: boolean }) =>
    api.post('/privacy/settings', settings),
  clearConversations: () => api.post('/privacy/clear/conversations'),
  clearDocuments: () => api.post('/privacy/clear/documents'),
  clearAll: () => api.post('/privacy/clear/all'),
}

// ─── Health ───────────────────────────────────────────────────────
export const healthAPI = {
  check: () => api.get('/health'),
}

export default api
