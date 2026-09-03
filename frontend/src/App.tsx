import { useEffect, useState } from 'react'
import ChatPage from './pages/ChatPage'
import MemoryPage from './pages/MemoryPage'
import SearchPage from './pages/SearchPage'
import { authStatusRequired, getAccessCode, setAccessCode, listConversations } from './api'

type Tab = 'chat' | 'memory' | 'search'

function AccessGate({ onPass }: { onPass: () => void }) {
  const [code, setCode] = useState('')
  const [error, setError] = useState('')
  const [checking, setChecking] = useState(false)

  const submit = async () => {
    if (!code.trim() || checking) return
    setChecking(true)
    setError('')
    setAccessCode(code)
    try {
      // 用一个真实接口验证口令
      await listConversations()
      onPass()
    } catch {
      setError('口令不正确，请重试（口令见简历/GitHub 说明）')
    } finally {
      setChecking(false)
    }
  }

  return (
    <div className="gate-wrap">
      <div className="gate-card">
        <div className="gate-logo">
          <span className="leaf">
            <svg viewBox="0 0 24 24" fill="currentColor" width="26" height="26">
              <path d="M17 8C8 10 5.9 16.17 3.82 21.34l1.89.66.95-2.3c.48.17.98.3 1.34.3C19 20 22 3 22 3c-1 2-8 2.25-13 3.25S2 11.5 2 13.5s1.75 3.75 1.75 3.75C3 8 17 8 17 8z" />
            </svg>
          </span>
          5 年后的我
        </div>
        <p className="gate-desc">
          这是一个演示站点，内置虚构演示人格。<br />
          输入访问口令进入（口令附在简历 / GitHub README 中）。
        </p>
        <input
          className="gate-input"
          type="password"
          placeholder="访问口令"
          value={code}
          autoFocus
          onChange={(e) => setCode(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && submit()}
        />
        {error && <div className="gate-error">{error}</div>}
        <button className="gate-btn" onClick={submit} disabled={checking || !code.trim()}>
          {checking ? '验证中…' : '进入'}
        </button>
      </div>
    </div>
  )
}

function App() {
  const [tab, setTab] = useState<Tab>('chat')
  // null = 启动探测中；false = 无需口令或口令已通过
  const [needAuth, setNeedAuth] = useState<boolean | null>(null)
  const [authed, setAuthed] = useState(false)

  useEffect(() => {
    authStatusRequired()
      .then((required) => {
        setNeedAuth(required)
        if (!required || getAccessCode()) setAuthed(true)
      })
      .catch(() => {
        // 探测失败（如本地未起后端）不挡 UI
        setNeedAuth(false)
        setAuthed(true)
      })
    const onFail = () => {
      setNeedAuth(true)
      setAuthed(false)
    }
    window.addEventListener('auth:failed', onFail)
    return () => window.removeEventListener('auth:failed', onFail)
  }, [])

  if (needAuth === null) {
    return <div className="gate-wrap"><div className="gate-loading">加载中…</div></div>
  }
  if (needAuth && !authed) {
    return <AccessGate onPass={() => setAuthed(true)} />
  }

  return (
    <div className="app">
      <header className="app-header">
        <div className="app-logo">
          <span className="leaf">
            <svg viewBox="0 0 24 24" fill="currentColor" width="22" height="22">
              <path d="M17 8C8 10 5.9 16.17 3.82 21.34l1.89.66.95-2.3c.48.17.98.3 1.34.3C19 20 22 3 22 3c-1 2-8 2.25-13 3.25S2 11.5 2 13.5s1.75 3.75 1.75 3.75C3 8 17 8 17 8z" />
            </svg>
          </span>
          5 年后的我
        </div>
        <nav className="app-tabs">
          <button className={`tab ${tab === 'chat' ? 'active' : ''}`} onClick={() => setTab('chat')}>对话</button>
          <button className={`tab ${tab === 'memory' ? 'active' : ''}`} onClick={() => setTab('memory')}>记忆库</button>
          <button className={`tab ${tab === 'search' ? 'active' : ''}`} onClick={() => setTab('search')}>搜索总结</button>
        </nav>
      </header>
      <main className="app-main">
        {tab === 'chat' && <ChatPage />}
        {tab === 'memory' && <MemoryPage />}
        {tab === 'search' && <SearchPage />}
      </main>
    </div>
  )
}

export default App
