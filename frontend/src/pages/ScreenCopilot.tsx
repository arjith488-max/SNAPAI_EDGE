import { useState, useRef, useCallback } from 'react'
import { useDropzone } from 'react-dropzone'

type CaptureMode = 'upload' | 'camera'
type Task = 'explain' | 'ocr' | 'errors' | 'diagram' | 'code' | 'summarize' | 'ask'

const TASKS: { id: Task; label: string; prompt: string }[] = [
  { id: 'explain',  label: '🔍 Explain',     prompt: 'Explain what is shown in this screenshot in detail.' },
  { id: 'ocr',      label: '📝 OCR / Text',  prompt: 'Extract all visible text from this image.' },
  { id: 'errors',   label: '🐛 Debug Error', prompt: 'I see an error or issue. Identify it and suggest a fix.' },
  { id: 'diagram',  label: '🔀 Diagram',     prompt: 'Explain this diagram or flowchart.' },
  { id: 'code',     label: '💻 Code',        prompt: 'Analyze the code shown. Explain what it does and suggest improvements.' },
  { id: 'summarize',label: '📋 Summarize',   prompt: 'Summarize the key information visible.' },
  { id: 'ask',      label: '❓ Ask',         prompt: '' },
]

export default function ScreenCopilot() {
  const [mode, setMode] = useState<CaptureMode>('upload')
  const [preview, setPreview] = useState<string | null>(null)
  const [file, setFile] = useState<File | null>(null)
  const [task, setTask] = useState<Task>('explain')
  const [customQ, setCustomQ] = useState('')
  const [result, setResult] = useState('')
  const [loading, setLoading] = useState(false)
  const [cameraOn, setCameraOn] = useState(false)
  const videoRef = useRef<HTMLVideoElement>(null)
  const streamRef = useRef<MediaStream | null>(null)

  const onDrop = useCallback((files: File[]) => {
    if (!files[0]) return
    setFile(files[0])
    setPreview(URL.createObjectURL(files[0]))
    setResult('')
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({ onDrop, accept: { 'image/*': [] }, multiple: false })

  const startCamera = async () => {
    const stream = await navigator.mediaDevices.getUserMedia({ video: true })
    streamRef.current = stream
    setCameraOn(true)
    setTimeout(() => { if (videoRef.current) videoRef.current.srcObject = stream }, 100)
  }

  const capture = () => {
    if (!videoRef.current) return
    const c = document.createElement('canvas')
    c.width  = videoRef.current.videoWidth
    c.height = videoRef.current.videoHeight
    c.getContext('2d')?.drawImage(videoRef.current, 0, 0)
    c.toBlob(blob => {
      if (!blob) return
      const f = new File([blob], 'screen.jpg', { type: 'image/jpeg' })
      setFile(f); setPreview(c.toDataURL()); setCameraOn(false)
      streamRef.current?.getTracks().forEach(t => t.stop())
      setResult('')
    }, 'image/jpeg')
  }

  const analyze = async () => {
    if (!file) return
    const activeTask = TASKS.find(t => t.id === task)!
    const prompt = task === 'ask' ? (customQ || 'What do you see?') : activeTask.prompt
    setLoading(true); setResult('')
    try {
      const form = new FormData()
      form.append('file', file)
      form.append('prompt', prompt)
      form.append('task', task)
      const r = await fetch('/api/ai/vision', { method: 'POST', body: form })
      const d = await r.json()
      setResult(d.content || d.text || d.error || 'No result returned')
    } catch (e: unknown) {
      setResult(`Error: ${e instanceof Error ? e.message : 'Unknown error'}`)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="page-pad">
      <div className="page-header">
        <h1 className="page-title">🖥️ Screen Copilot</h1>
        <p className="page-subtitle">Capture a screenshot or upload an image — AI explains, debugs, or reads it</p>
      </div>

      <div className="g2" style={{ alignItems: 'start' }}>
        {/* Left: Capture */}
        <div>
          {cameraOn ? (
            <div className="card card-p" style={{ textAlign: 'center' }}>
              <video ref={videoRef} autoPlay playsInline style={{ width: '100%', borderRadius: 'var(--r-md)', maxHeight: 300 }} />
              <div className="flex gap-2 mt-3" style={{ justifyContent: 'center' }}>
                <button className="btn btn-primary" onClick={capture}>📸 Capture</button>
                <button className="btn btn-secondary" onClick={() => { setCameraOn(false); streamRef.current?.getTracks().forEach(t=>t.stop()) }}>Cancel</button>
              </div>
            </div>
          ) : (
            <div {...getRootProps()} className={`dropzone${isDragActive ? ' dragging' : ''}`}>
              <input {...getInputProps()} />
              {preview
                ? <img src={preview} alt="Preview" style={{ maxHeight: 300, borderRadius: 'var(--r-md)', objectFit: 'contain', width: '100%' }} />
                : <>
                    <div className="dropzone-icon">🖥️</div>
                    <div className="dropzone-text"><strong>Drop a screenshot here</strong> or click to select</div>
                  </>
              }
            </div>
          )}

          <div className="flex gap-2 mt-3">
            <button className="btn btn-secondary btn-sm" onClick={startCamera}>📷 Camera</button>
            {preview && <button className="btn btn-ghost btn-sm" onClick={() => { setFile(null); setPreview(null); setResult('') }}>Clear</button>}
          </div>

          {/* Tasks */}
          <div className="card card-p mt-3">
            <div className="fw-500 text-sm mb-3">What should AI do?</div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 12 }}>
              {TASKS.map(t => (
                <button key={t.id} className={`btn btn-sm ${task === t.id ? 'btn-primary' : 'btn-secondary'}`} onClick={() => setTask(t.id)}>
                  {t.label}
                </button>
              ))}
            </div>
            {task === 'ask' && (
              <input className="input mb-3" placeholder="Ask a specific question..." value={customQ} onChange={e => setCustomQ(e.target.value)} />
            )}
            <button className="btn btn-primary w-full" onClick={analyze} disabled={!file || loading}>
              {loading ? 'Analyzing...' : '🔍 Analyze'}
            </button>
          </div>
        </div>

        {/* Right: Result */}
        <div className="card card-p" style={{ minHeight: 400 }}>
          <div className="fw-600 text-sm mb-4">Analysis Result</div>
          {loading && (
            <div className="empty-state">
              <div className="typing-dots"><span /><span /><span /></div>
              <div className="text-xs text-muted">Analyzing...</div>
            </div>
          )}
          {!loading && !result && (
            <div className="empty-state">
              <div className="empty-state-icon">🖥️</div>
              <div className="empty-state-title">Upload or capture a screenshot</div>
              <div className="empty-state-sub">Then choose what AI should do with it</div>
            </div>
          )}
          {result && !loading && (
            <div style={{ fontSize: '0.875rem', lineHeight: 1.8, color: 'var(--text-secondary)', whiteSpace: 'pre-wrap' }}>
              {result}
            </div>
          )}
        </div>
      </div>

      <div className="alert alert-warning mt-4">
        <span>⚠️</span>
        <span><strong>SnapAI will never execute code it generates.</strong> All commands are displayed for review only.</span>
      </div>
    </div>
  )
}
