import React, { createContext, useContext, useState, useEffect, useCallback } from 'react'
import { hardwareAPI, privacyAPI, aiAPI, ProviderItem } from '../services/api'

export type ThemeMode = 'light' | 'dark' | 'system'

interface AppState {
  aiMode: 'local' | 'cloud' | 'hybrid' | 'offline'
  activeProvider: string
  activeModel: string
  isOnline: boolean
  ollamaAvailable: boolean
  jinaConfigured: boolean
  providers: ProviderItem[]
  privacyMode: string
  cloudEnabled: boolean
  deviceInfo: Record<string, unknown> | null
  loading: boolean
  theme: ThemeMode
  resolvedTheme: 'light' | 'dark'
}

interface AppContextType extends AppState {
  refresh: () => void
  setAiMode: (mode: 'local' | 'cloud' | 'hybrid' | 'offline') => void
  setTheme: (theme: ThemeMode) => void
}

const AppContext = createContext<AppContextType | null>(null)

export function AppProvider({ children }: { children: React.ReactNode }) {
  const getInitialTheme = (): ThemeMode => {
    try {
      const stored = localStorage.getItem('snapai_theme') as ThemeMode
      if (stored === 'light' || stored === 'dark' || stored === 'system') return stored
    } catch {}
    return 'system'
  }

  const getSystemTheme = (): 'light' | 'dark' => {
    if (typeof window !== 'undefined' && window.matchMedia && window.matchMedia('(prefers-color-scheme: light)').matches) {
      return 'light'
    }
    return 'dark'
  }

  const initialTheme = getInitialTheme()
  const initialResolved = initialTheme === 'system' ? getSystemTheme() : initialTheme

  const [state, setState] = useState<AppState>({
    aiMode: 'local',
    activeProvider: 'Auto Router',
    activeModel: 'Auto',
    isOnline: true,
    ollamaAvailable: false,
    jinaConfigured: true,
    providers: [],
    privacyMode: 'local_first',
    cloudEnabled: true,
    deviceInfo: null,
    loading: true,
    theme: initialTheme,
    resolvedTheme: initialResolved,
  })

  // Theme synchronization effect
  useEffect(() => {
    const applyTheme = (theme: ThemeMode) => {
      const resolved = theme === 'system' ? getSystemTheme() : theme
      setState(prev => ({ ...prev, theme, resolvedTheme: resolved }))
      const root = document.documentElement
      if (resolved === 'light') {
        root.classList.add('theme-light')
        root.classList.remove('theme-dark')
      } else {
        root.classList.add('theme-dark')
        root.classList.remove('theme-light')
      }
    }

    applyTheme(state.theme)

    const mediaQuery = window.matchMedia('(prefers-color-scheme: light)')
    const handleSystemChange = () => {
      if (state.theme === 'system') {
        applyTheme('system')
      }
    }

    mediaQuery.addEventListener('change', handleSystemChange)
    return () => mediaQuery.removeEventListener('change', handleSystemChange)
  }, [state.theme])

  const setTheme = (newTheme: ThemeMode) => {
    try {
      localStorage.setItem('snapai_theme', newTheme)
    } catch {}
    const resolved = newTheme === 'system' ? getSystemTheme() : newTheme
    setState(prev => ({ ...prev, theme: newTheme, resolvedTheme: resolved }))
  }

  const refresh = useCallback(async () => {
    try {
      const [statusRes, privacyRes] = await Promise.allSettled([
        aiAPI.status(),
        privacyAPI.status(),
      ])

      const status = statusRes.status === 'fulfilled' ? statusRes.value.data : {}
      const privacy = privacyRes.status === 'fulfilled' ? privacyRes.value.data : {}

      const providersList: ProviderItem[] = status.providers || []
      const ollama = providersList.find(p => p.provider === 'ollama')
      const openai = providersList.find(p => p.provider === 'openai')
      const gemini = providersList.find(p => p.provider === 'gemini')

      let providerName = 'Local'
      let modelName = 'Ollama'

      const mode = status.active_mode || 'local'
      if (mode === 'offline') {
        providerName = 'Local'
        modelName = (status.installed_local_models && status.installed_local_models[0]) || 'Local model active'
      } else if (mode === 'local') {
        providerName = 'Ollama'
        modelName = (status.installed_local_models && status.installed_local_models[0]) || ollama?.active_model || 'Local LLM'
      } else if (mode === 'cloud') {
        if (gemini?.available) {
          providerName = 'Gemini'
          modelName = gemini.active_model || 'gemini-1.5-flash'
        } else if (openai?.available) {
          providerName = 'OpenAI'
          modelName = openai.active_model || 'gpt-4o-mini'
        }
      } else if (mode === 'hybrid') {
        providerName = 'Hybrid'
        modelName = 'Local RAG + Cloud'
      }

      setState(prev => ({
        ...prev,
        isOnline: status.online ?? prev.isOnline,
        ollamaAvailable: ollama?.available ?? false,
        providers: providersList,
        activeProvider: providerName,
        activeModel: modelName,
        aiMode: (status.active_mode ?? 'local') as AppState['aiMode'],
        privacyMode: privacy.privacy_mode ?? 'local_first',
        cloudEnabled: privacy.cloud_enabled ?? true,
        loading: false,
      }))
    } catch {
      setState(prev => ({ ...prev, loading: false }))
    }
  }, [])

  const fetchDevice = useCallback(async () => {
    try {
      const res = await hardwareAPI.info()
      setState(prev => ({ ...prev, deviceInfo: res.data }))
    } catch {
      setState(prev => ({ ...prev, deviceInfo: null }))
    }
  }, [])

  useEffect(() => {
    refresh()
    fetchDevice()
    const interval = setInterval(refresh, 25000)
    return () => clearInterval(interval)
  }, [refresh, fetchDevice])

  const setAiMode = (mode: AppState['aiMode']) => {
    setState(prev => ({ ...prev, aiMode: mode }))
  }

  return (
    <AppContext.Provider value={{ ...state, refresh, setAiMode, setTheme }}>
      {children}
    </AppContext.Provider>
  )
}

export const useApp = () => {
  const ctx = useContext(AppContext)
  if (!ctx) throw new Error('useApp must be used inside AppProvider')
  return ctx
}
