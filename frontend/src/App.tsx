import { Routes, Route, NavLink, useNavigate } from 'react-router-dom'
import { useState } from 'react'
import { useApp } from './hooks/useAppContext'
import { BubbleStatus } from './components/bubbles'

// Pages
import Dashboard   from './pages/Dashboard'
import Chat        from './pages/Chat'
import Vision      from './pages/Vision'
import Documents   from './pages/Documents'
import Voice       from './pages/Voice'
import KnowledgeBase from './pages/KnowledgeBase'
import Models      from './pages/Models'
import Benchmark   from './pages/Benchmark'
import Privacy     from './pages/Privacy'
import Settings    from './pages/Settings'
import AIRouter    from './pages/AIRouter'
import ScreenCopilot from './pages/ScreenCopilot'
import Developer   from './pages/Developer'
import Device      from './pages/Device'
import ContextPanel from './components/ContextPanel'

// ── Nav items ─────────────────────────────────────────────────────
const NAV = [
  { section: 'Home', items: [
    { to: '/',          icon: '⚡', label: 'Dashboard' },
  ]},
  { section: 'Workspace', items: [
    { to: '/chat',      icon: '💬', label: 'AI Chat' },
    { to: '/vision',    icon: '👁️',  label: 'Vision' },
    { to: '/screen',    icon: '🖥️',  label: 'Screen Copilot' },
    { to: '/voice',     icon: '🎤', label: 'Voice' },
    { to: '/documents', icon: '📄', label: 'Documents' },
  ]},
  { section: 'AI System', items: [
    { to: '/knowledge', icon: '🧠', label: 'Knowledge' },
    { to: '/router',    icon: '🔀', label: 'AI Router' },
    { to: '/models',    icon: '🤖', label: 'Models' },
    { to: '/benchmark', icon: '📊', label: 'Benchmark' },
    { to: '/developer', icon: '👨‍💻', label: 'Developer' },
  ]},
  { section: 'Security', items: [
    { to: '/privacy',   icon: '🔒', label: 'Privacy Guard' },
  ]},
  { section: 'System', items: [
    { to: '/device',    icon: '💻', label: 'Device' },
    { to: '/settings',  icon: '⚙️',  label: 'Settings' },
  ]},
]

// ── Floating AI Status Bubble ─────────────────────────────────────
function TopbarAIStatus() {
  const { aiMode, isOnline, activeProvider, activeModel } = useApp()
  const m = !isOnline ? 'offline' : aiMode

  const subText = m === 'hybrid'
    ? 'Local RAG + Cloud Reasoning'
    : m === 'offline'
    ? 'Air-Gapped Local Model Active'
    : `${activeProvider} · ${activeModel}`

  return (
    <BubbleStatus
      mode={m}
      sublabel={subText}
    />
  )
}

// ── Theme Switcher Bubble ─────────────────────────────────────────
function ThemeToggle() {
  const { theme, setTheme, resolvedTheme } = useApp()

  const cycleTheme = () => {
    if (theme === 'system') setTheme('light')
    else if (theme === 'light') setTheme('dark')
    else setTheme('system')
  }

  const icon = theme === 'system' ? '💻' : resolvedTheme === 'light' ? '☀️' : '🌙'
  const title = `Theme: ${theme.toUpperCase()} (Click to toggle Light / Dark / System)`

  return (
    <button
      className="btn btn-ghost btn-icon-sm"
      title={title}
      onClick={cycleTheme}
      aria-label="Toggle theme"
    >
      <span style={{ fontSize: '15px' }}>{icon}</span>
    </button>
  )
}

export default function App() {
  const [contextOpen, setContextOpen] = useState(true)
  const navigate = useNavigate()

  return (
    <div className="app-shell">
      {/* ── Floating Header Bubble ───────────────────────── */}
      <header className="topbar">
        {/* Left: Brand Bubble */}
        <div className="topbar-left">
          <div className="logo-bubble" onClick={() => navigate('/')} style={{ cursor: 'pointer' }}>
            <div className="logo-mark">S</div>
            <div>
              <div className="logo-text">SnapAI Edge</div>
              <div className="logo-sub">Snapdragon AI Lab</div>
            </div>
          </div>
        </div>

        {/* Center: Floating AI Status Bubble */}
        <div className="topbar-center">
          <TopbarAIStatus />
        </div>

        {/* Right: Quick Action Bubbles */}
        <div className="topbar-right">
          <button
            className="btn btn-ghost btn-icon-sm"
            title="AI Chat"
            onClick={() => navigate('/chat')}
            aria-label="Open AI Chat"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
            </svg>
          </button>
          <button
            className="btn btn-ghost btn-icon-sm"
            title="Privacy Guard"
            onClick={() => navigate('/privacy')}
            aria-label="Open Privacy Guard"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
            </svg>
          </button>
          <ThemeToggle />
          <button
            className="btn btn-ghost btn-icon-sm"
            title="Toggle Live Telemetry Context"
            onClick={() => setContextOpen(p => !p)}
            style={{ color: contextOpen ? 'var(--brand-400)' : undefined }}
            aria-label="Toggle Context Panel"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <rect x="3" y="3" width="18" height="18" rx="2" />
              <path d="M16 3v18" />
            </svg>
          </button>
          <button
            className="btn btn-ghost btn-icon-sm"
            title="Settings"
            onClick={() => navigate('/settings')}
            aria-label="Open Settings"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="3" />
              <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
            </svg>
          </button>
        </div>
      </header>

      {/* ── Body ─────────────────────────────────────────── */}
      <div className="app-body">
        {/* Floating Sidebar Bubble */}
        <nav className="sidebar">
          {NAV.map(section => (
            <div key={section.section} className="sidebar-section">
              <div className="sidebar-section-label">{section.section}</div>
              {section.items.map(item => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={item.to === '/'}
                  className={({ isActive }) => `nav-link${isActive ? ' active' : ''}`}
                >
                  <span className="nav-icon">{item.icon}</span>
                  <span>{item.label}</span>
                </NavLink>
              ))}
            </div>
          ))}

          {/* Footer Bubble */}
          <div className="sidebar-footer">
            <div className="text-xs fw-600 text-secondary">SnapAI Edge v1.0</div>
            <div className="text-xs text-muted mt-1">Qualcomm AI Challenge</div>
          </div>
        </nav>

        {/* Floating Main Workspace Bubble */}
        <main className="main-area">
          <div className="page-scroll">
            <Routes>
              <Route path="/"          element={<Dashboard />} />
              <Route path="/chat"      element={<Chat />} />
              <Route path="/vision"    element={<Vision />} />
              <Route path="/screen"    element={<ScreenCopilot />} />
              <Route path="/voice"     element={<Voice />} />
              <Route path="/documents" element={<Documents />} />
              <Route path="/knowledge" element={<KnowledgeBase />} />
              <Route path="/router"    element={<AIRouter />} />
              <Route path="/models"    element={<Models />} />
              <Route path="/benchmark" element={<Benchmark />} />
              <Route path="/developer" element={<Developer />} />
              <Route path="/privacy"   element={<Privacy />} />
              <Route path="/device"    element={<Device />} />
              <Route path="/settings"  element={<Settings />} />
            </Routes>
          </div>
        </main>

        {/* Floating Context Panel Bubble */}
        <aside className={`context-panel${contextOpen ? '' : ' collapsed'}`} aria-label="Context and Metrics">
          <ContextPanel />
        </aside>
      </div>
    </div>
  )
}
