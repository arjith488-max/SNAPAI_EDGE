import { useState, useRef } from 'react'
import { voiceAPI, chatAPI } from '../services/api'
import { BubbleBadge, BubbleCard, BubbleButton } from '../components/bubbles'

type RecordState = 'idle' | 'recording' | 'processing' | 'done' | 'error'

export default function Voice() {
  const [recState, setRecState] = useState<RecordState>('idle')
  const [transcript, setTranscript] = useState('')
  const [aiResponse, setAiResponse] = useState('')
  const [mode, setMode] = useState<string>('')
  const [latency, setLatency] = useState<number | null>(null)
  const [error, setError] = useState('')
  const [language] = useState('en')
  const mediaRecorder = useRef<MediaRecorder | null>(null)
  const chunks = useRef<Blob[]>([])

  const startRecording = async () => {
    setError('')
    setTranscript('')
    setAiResponse('')
    chunks.current = []
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const mr = new MediaRecorder(stream, { mimeType: 'audio/webm' })
      mr.ondataavailable = e => { if (e.data.size > 0) chunks.current.push(e.data) }
      mr.onstop = async () => {
        stream.getTracks().forEach(t => t.stop())
        await processAudio()
      }
      mr.start()
      mediaRecorder.current = mr
      setRecState('recording')
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : 'Unknown'
      setError(`Microphone error: ${msg}. Please grant microphone permission.`)
      setRecState('error')
    }
  }

  const stopRecording = () => {
    mediaRecorder.current?.stop()
    setRecState('processing')
  }

  const processAudio = async () => {
    const blob = new Blob(chunks.current, { type: 'audio/webm' })
    const audioFile = new File([blob], 'recording.webm', { type: 'audio/webm' })
    try {
      // Transcribe
      const tRes = await voiceAPI.transcribe(audioFile, language)
      const text = tRes.data.text || ''
      setTranscript(text)
      if (!text.trim()) {
        setError('No speech detected. Please speak clearly and try again.')
        setRecState('error')
        return
      }
      // Get AI response
      const aRes = await chatAPI.send(text, undefined, false)
      setAiResponse(aRes.data.content)
      setMode(aRes.data.mode)
      setLatency(aRes.data.latency_ms)
      // TTS via browser Web Speech API
      speakText(aRes.data.content)
      setRecState('done')
    } catch (e: unknown) {
      setError(`Processing failed: ${e instanceof Error ? e.message : 'Unknown'}`)
      setRecState('error')
    }
  }

  const speakText = (text: string) => {
    if (!('speechSynthesis' in window)) return
    window.speechSynthesis.cancel()
    const utt = new SpeechSynthesisUtterance(text.slice(0, 500))
    utt.lang = language
    utt.rate = 0.95
    window.speechSynthesis.speak(utt)
  }

  const reset = () => {
    window.speechSynthesis.cancel()
    setRecState('idle')
    setTranscript('')
    setAiResponse('')
    setError('')
    setLatency(null)
  }

  return (
    <div className="page-pad">
      <div className="page-header">
        <h1 className="page-title">🎤 Voice AI Studio</h1>
        <p className="page-subtitle">Interactive Real-Time Speech Recognition · Edge Intelligence · Local TTS Synthesis</p>
      </div>

      <div style={{ maxWidth: 700, margin: '0 auto', display: 'flex', flexDirection: 'column', gap: 20 }}>
        {/* Large Animated Voice Bubble Card */}
        <BubbleCard
          variant="elevated"
          style={{
            padding: '48px 24px',
            textAlign: 'center',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            borderRadius: 'var(--bubble-radius-xl)',
            boxShadow: 'var(--bubble-shadow-floating)',
          }}
        >
          {/* Pulsing Voice Orb Button */}
          <div style={{ position: 'relative', margin: '0 auto 28px' }}>
            <button
              className={`voice-btn ${recState === 'recording' ? 'recording' : ''}`}
              style={{
                opacity: recState === 'processing' ? 0.7 : 1,
                cursor: recState === 'processing' ? 'wait' : 'pointer',
              }}
              onClick={recState === 'idle' || recState === 'done' || recState === 'error'
                ? startRecording
                : recState === 'recording' ? stopRecording : undefined}
              title={recState === 'recording' ? 'Click to stop' : 'Click to speak'}
              aria-label="Toggle voice recording"
            >
              {recState === 'recording' ? '⏹' : recState === 'processing' ? '⏳' : '🎤'}
            </button>
          </div>

          <div style={{ fontSize: '1.2rem', fontWeight: 800, color: 'var(--text-primary)', marginBottom: 6 }}>
            {recState === 'idle'       && 'Tap to speak'}
            {recState === 'recording'  && 'Listening... Click to stop'}
            {recState === 'processing' && 'Processing speech on device...'}
            {recState === 'done'       && 'Response ready'}
            {recState === 'error'      && 'Recording failed'}
          </div>

          <div className="flex items-center gap-2 justify-center text-xs text-muted">
            <span className="net-dot online" />
            <span>English (en) · Local Web Speech Synthesis</span>
          </div>

          {(recState === 'done' || recState === 'error') && (
            <div className="mt-4">
              <BubbleButton variant="primary" size="sm" onClick={reset}>
                🔄 New Recording
              </BubbleButton>
            </div>
          )}
        </BubbleCard>

        {error && (
          <div style={{ padding: 14, background: 'rgba(239, 68, 68, 0.12)', color: '#f87171', borderRadius: 'var(--bubble-radius-md)', fontSize: '0.85rem' }}>
            {error}
          </div>
        )}

        {/* Live Speech Transcript Bubble */}
        {transcript && (
          <BubbleCard variant="glass" style={{ padding: 22 }}>
            <div className="fw-700 text-sm mb-2" style={{ color: 'var(--text-muted)' }}>
              📝 Recognized Speech
            </div>
            <p style={{ color: 'var(--text-primary)', fontSize: '1.05rem', fontWeight: 600, lineHeight: 1.6 }}>
              "{transcript}"
            </p>
          </BubbleCard>
        )}

        {/* AI Voice Response Bubble */}
        {aiResponse && (
          <BubbleCard variant="elevated" style={{ padding: 24 }}>
            <div className="flex justify-between items-center mb-3">
              <div className="fw-800 text-base" style={{ color: 'var(--text-primary)' }}>
                ⚡ Assistant Response
              </div>
              <div className="flex gap-2 items-center">
                {mode && (
                  <BubbleBadge variant={mode.toLowerCase() as any}>
                    {mode.toUpperCase()}
                  </BubbleBadge>
                )}
                {latency && <span className="text-xs text-green fw-600">⏱ {latency} ms</span>}
              </div>
            </div>
            <p style={{ color: 'var(--text-secondary)', lineHeight: 1.75, fontSize: '0.94rem' }}>
              {aiResponse}
            </p>
            <div className="flex gap-2 mt-4">
              <BubbleButton variant="secondary" size="sm" onClick={() => speakText(aiResponse)}>
                🔊 Replay Audio
              </BubbleButton>
              <BubbleButton variant="ghost" size="sm" onClick={() => window.speechSynthesis.cancel()}>
                🔇 Stop
              </BubbleButton>
            </div>
          </BubbleCard>
        )}

        {/* How Voice Works Bubble */}
        <BubbleCard variant="subtle" style={{ padding: 20 }}>
          <div className="fw-700 text-sm mb-3" style={{ color: 'var(--text-primary)' }}>
            ℹ️ Voice Processing Pipeline
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: 10 }}>
            {[
              ['1. Audio In', 'Browser MediaRecorder'],
              ['2. Whisper STT', 'Local Faster-Whisper'],
              ['3. AI Router', 'Dynamic Inference'],
              ['4. TTS Output', 'SpeechSynthesis API'],
            ].map(([title, desc]) => (
              <div key={title} style={{ padding: 10, background: 'var(--bubble-bg-sunken)', borderRadius: 'var(--bubble-radius-md)', border: '1px solid var(--bubble-border-subtle)' }}>
                <div className="fw-700 text-xs" style={{ color: 'var(--brand-400)' }}>{title}</div>
                <div className="text-xs text-muted mt-1">{desc}</div>
              </div>
            ))}
          </div>
        </BubbleCard>
      </div>
    </div>
  )
}
