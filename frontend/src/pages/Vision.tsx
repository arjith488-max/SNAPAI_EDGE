import { useState, useRef, useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import { visionAPI } from '../services/api'
import { BubbleBadge, BubbleCard, BubbleButton } from '../components/bubbles'

const TASKS = [
  { id: 'describe',  label: '🔍 Describe', prompt: 'Describe this image in detail.' },
  { id: 'ocr',       label: '📝 OCR',      prompt: 'Extract all text from this image.' },
  { id: 'diagram',   label: '🔀 Diagram',  prompt: 'Explain this diagram.' },
  { id: 'chart',     label: '📊 Chart',    prompt: 'Analyze this chart/graph.' },
  { id: 'objects',   label: '🎯 Objects',  prompt: 'Identify key objects in this image.' },
  { id: 'summarize', label: '📋 Summarize',prompt: 'Summarize what this image shows.' },
  { id: 'vqa',       label: '❓ Ask',      prompt: '' },
]

interface VisionResult {
  task: string
  content?: string
  text?: string
  mode?: string
  model?: string
  latency_ms?: number
  error?: string
}

export default function Vision() {
  const [file, setFile] = useState<File | null>(null)
  const [preview, setPreview] = useState<string | null>(null)
  const [task, setTask] = useState('describe')
  const [customPrompt, setCustomPrompt] = useState('')
  const [result, setResult] = useState<VisionResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [cameraOpen, setCameraOpen] = useState(false)
  const [preferLocal, setPreferLocal] = useState(false)
  const videoRef = useRef<HTMLVideoElement>(null)
  const streamRef = useRef<MediaStream | null>(null)

  const onDrop = useCallback((accepted: File[]) => {
    if (!accepted[0]) return
    setFile(accepted[0])
    setResult(null)
    const url = URL.createObjectURL(accepted[0])
    setPreview(url)
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'image/*': ['.jpg', '.jpeg', '.png', '.webp'] },
    multiple: false,
  })

  const openCamera = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true })
      streamRef.current = stream
      setCameraOpen(true)
      setTimeout(() => {
        if (videoRef.current) videoRef.current.srcObject = stream
      }, 100)
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : 'Unknown error'
      alert(`Camera error: ${msg}\n\nPlease allow camera access in your browser.`)
    }
  }

  const capturePhoto = () => {
    if (!videoRef.current) return
    const canvas = document.createElement('canvas')
    canvas.width = videoRef.current.videoWidth
    canvas.height = videoRef.current.videoHeight
    canvas.getContext('2d')?.drawImage(videoRef.current, 0, 0)
    canvas.toBlob(blob => {
      if (!blob) return
      const captured = new File([blob], 'camera_capture.jpg', { type: 'image/jpeg' })
      setFile(captured)
      setPreview(canvas.toDataURL())
      closeCamera()
      setResult(null)
    }, 'image/jpeg', 0.9)
  }

  const closeCamera = () => {
    streamRef.current?.getTracks().forEach(t => t.stop())
    streamRef.current = null
    setCameraOpen(false)
  }

  const analyze = async () => {
    if (!file) return
    const activeTask = TASKS.find(t => t.id === task)!
    const prompt = task === 'vqa' ? (customPrompt || 'What do you see?') : activeTask.prompt
    setLoading(true)
    setResult(null)
    try {
      const r = await visionAPI.analyze(file, prompt, task, preferLocal)
      setResult(r.data)
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : 'Unknown'
      setResult({ task, error: `Analysis failed: ${msg}` })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="page-pad">
      <div className="page-header">
        <h1 className="page-title">👁️ Vision Workspace</h1>
        <p className="page-subtitle">Multimodal Edge Intelligence · OCR · Diagram & Chart Analysis · Visual Q&A</p>
      </div>

      <div className="g2" style={{ alignItems: 'start', gap: 20 }}>
        {/* Left: Central Vision Bubble & Floating Controls */}
        <div className="flex flex-col gap-4">
          <BubbleCard
            variant="elevated"
            style={{
              padding: 24,
              textAlign: 'center',
              position: 'relative',
              minHeight: 340,
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'center',
              alignItems: 'center',
            }}
          >
            {cameraOpen ? (
              <div style={{ width: '100%' }}>
                <video
                  ref={videoRef}
                  autoPlay
                  playsInline
                  style={{ width: '100%', borderRadius: 'var(--bubble-radius-lg)', maxHeight: 320, objectFit: 'cover' }}
                />
                <div className="flex gap-2 mt-4 justify-center">
                  <BubbleButton variant="primary" size="sm" onClick={capturePhoto}>
                    📸 Capture Frame
                  </BubbleButton>
                  <BubbleButton variant="secondary" size="sm" onClick={closeCamera}>
                    ✕ Close Camera
                  </BubbleButton>
                </div>
              </div>
            ) : (
              <div
                {...getRootProps()}
                className={`dropzone w-full ${isDragActive ? 'dragging' : ''}`}
                style={{ padding: 28, background: 'transparent', border: 'none' }}
              >
                <input {...getInputProps()} />
                {preview ? (
                  <div style={{ position: 'relative', display: 'inline-block' }}>
                    <img
                      src={preview}
                      alt="Preview"
                      style={{
                        maxWidth: '100%',
                        maxHeight: 280,
                        borderRadius: 'var(--bubble-radius-md)',
                        objectFit: 'contain',
                        boxShadow: 'var(--bubble-shadow-floating)',
                      }}
                    />
                  </div>
                ) : (
                  <div>
                    <div style={{ fontSize: '3rem', marginBottom: 12, opacity: 0.6 }}>📷</div>
                    <div style={{ fontSize: '1rem', fontWeight: 700, color: 'var(--text-primary)', marginBottom: 4 }}>
                      Central Vision Bubble
                    </div>
                    <div className="text-xs text-muted">
                      Drop an image here or click to browse (PNG, JPG, WebP)
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Floating Camera & Control Buttons */}
            <div className="flex gap-2 mt-2" style={{ justifyContent: 'center' }}>
              {!cameraOpen && (
                <BubbleButton variant="secondary" size="sm" onClick={openCamera}>
                  📷 Live Camera
                </BubbleButton>
              )}
              {preview && (
                <BubbleButton
                  variant="ghost"
                  size="sm"
                  onClick={() => { setFile(null); setPreview(null); setResult(null) }}
                >
                  ✕ Clear
                </BubbleButton>
              )}
            </div>
          </BubbleCard>

          {/* Floating Task Selection Bubbles */}
          <BubbleCard variant="glass" style={{ padding: 20 }}>
            <div className="fw-700 text-sm mb-3" style={{ color: 'var(--text-primary)' }}>
              Analysis Tasks
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 16 }}>
              {TASKS.map(t => (
                <BubbleButton
                  key={t.id}
                  variant={task === t.id ? 'primary' : 'secondary'}
                  size="sm"
                  pill
                  onClick={() => setTask(t.id)}
                >
                  {t.label}
                </BubbleButton>
              ))}
            </div>

            {task === 'vqa' && (
              <input
                className="input-field w-full mb-3"
                placeholder="Ask anything about the image..."
                value={customPrompt}
                onChange={e => setCustomPrompt(e.target.value)}
              />
            )}

            <div className="flex justify-between items-center mt-2">
              <label className="flex gap-2 items-center text-xs text-muted" style={{ cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={preferLocal}
                  onChange={e => setPreferLocal(e.target.checked)}
                  style={{ accentColor: 'var(--brand-500)' }}
                />
                Prefer Local LLaVA / NPU
              </label>

              <BubbleButton
                variant="primary"
                size="md"
                onClick={analyze}
                disabled={!file || loading}
              >
                {loading ? '⏳ Analyzing...' : '🔍 Analyze Vision'}
              </BubbleButton>
            </div>
          </BubbleCard>
        </div>

        {/* Right: Results Bubble */}
        <BubbleCard variant="elevated" style={{ padding: 24, minHeight: 460 }}>
          <div className="flex justify-between items-center mb-4">
            <h3 className="fw-800 text-base" style={{ color: 'var(--text-primary)' }}>
              Analysis Result
            </h3>
            {result && (
              <div className="flex gap-2 items-center">
                {result.mode && (
                  <BubbleBadge variant={result.mode.toLowerCase() as any}>
                    {result.mode.toUpperCase()}
                  </BubbleBadge>
                )}
                {result.latency_ms && (
                  <span className="text-xs text-green fw-600">⏱ {result.latency_ms} ms</span>
                )}
              </div>
            )}
          </div>

          {loading && (
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: 280, gap: 14 }}>
              <div className="typing-dots"><span /><span /><span /></div>
              <p className="text-sm text-muted">Running multimodal analysis...</p>
            </div>
          )}

          {!loading && !result && (
            <div style={{ textAlign: 'center', color: 'var(--text-muted)', padding: '90px 20px' }}>
              <div style={{ fontSize: '3rem', opacity: 0.35, marginBottom: 12 }}>👁️</div>
              <div className="fw-600 text-sm" style={{ color: 'var(--text-secondary)' }}>No image analyzed yet</div>
              <p className="text-xs text-muted mt-1">Upload an image or capture a photo from camera to begin</p>
            </div>
          )}

          {result && !loading && (
            <div className="anim-slide-up">
              {result.error ? (
                <div style={{ padding: 14, background: 'rgba(239, 68, 68, 0.1)', color: '#f87171', borderRadius: 'var(--bubble-radius-md)', fontSize: '0.85rem' }}>
                  {result.error}
                </div>
              ) : (
                <div style={{ whiteSpace: 'pre-wrap', fontSize: '0.92rem', lineHeight: 1.75, color: 'var(--text-secondary)' }}>
                  {result.content || result.text}
                </div>
              )}
              {result.model && (
                <div className="meta-bubble mt-4">
                  <span className="text-muted text-xs">Vision Engine: </span>
                  <span className="fw-600 text-xs">{result.model}</span>
                </div>
              )}
            </div>
          )}
        </BubbleCard>
      </div>
    </div>
  )
}
