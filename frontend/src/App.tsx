import { useEffect, useState } from 'react'
import ChatPage from './pages/ChatPage'
import MemoryPage from './pages/MemoryPage'
import SearchPage from './pages/SearchPage'
import { authStatusRequired, getAccessCode, setAccessCode, listConversations } from './api'

type Tab = 'chat' | 'memory' | 'search'

function LeafIcon({ size = 22 }: { size?: number }) {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" width={size} height={size}>
      <path d="M17 8C8 10 5.9 16.17 3.82 21.34l1.89.66.95-2.3c.48.17.98.3 1.34.3C19 20 22 3 22 3c-1 2-8 2.25-13 3.25S2 11.5 2 13.5s1.75 3.75 1.75 3.75C3 8 17 8 17 8z" />
    </svg>
  )
}

function NavIcon({ name }: { name: Tab }) {
  const p = {
    viewBox: '0 0 24 24',
    fill: 'none',
    stroke: 'currentColor',
    strokeWidth: 1.8,
    strokeLinecap: 'round' as const,
    strokeLinejoin: 'round' as const,
    width: 20,
    height: 20,
  }
  if (name === 'chat') {
    return (
      <svg {...p}>
        <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z" />
      </svg>
    )
  }
  if (name === 'memory') {
    return (
      <svg {...p}>
        <path d="M12 2 2 7l10 5 10-5-10-5z" />
        <path d="M2 17l10 5 10-5" />
        <path d="M2 12l10 5 10-5" />
      </svg>
    )
  }
  return (
    <svg {...p}>
      <circle cx="11" cy="11" r="7" />
      <path d="M21 21l-4.35-4.35" />
    </svg>
  )
}

const NAV_ITEMS: { key: Tab; label: string; desc: string }[] = [
  { key: 'chat', label: '对话', desc: '和 5 年后的我聊聊' },
  { key: 'memory', label: '记忆库', desc: 'L1–L6 分层记忆' },
  { key: 'search', label: '搜索总结', desc: '回顾你的轨迹' },
]

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
      setError('口令不正确，请重试（口令见项目 README）')
    } finally {
      setChecking(false)
    }
  }

  return (
    <div className="gate-wrap">
      <div className="gate-card">
        <div className="gate-logo">
          <span className="leaf">
            <LeafIcon size={26} />
          </span>
          5 年后的我
        </div>
        <p className="gate-desc">
          这是一个演示站点，内置虚构演示人格。<br />
          输入访问口令进入（口令见项目 README）。
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
      {/* 桌面端：左侧边栏 */}
      <aside className="sidebar">
        <div className="sidebar-logo">
          <span className="leaf">
            <LeafIcon size={24} />
          </span>
          <div className="sidebar-logo-text">
            <div className="sidebar-title">5 年后的我</div>
            <div className="sidebar-sub">分层记忆 · 反谄媚视角</div>
          </div>
        </div>
        <nav className="sidebar-nav">
          {NAV_ITEMS.map((item) => (
            <button
              key={item.key}
              className={`nav-item ${tab === item.key ? 'active' : ''}`}
              onClick={() => setTab(item.key)}
            >
              <span className="nav-icon"><NavIcon name={item.key} /></span>
              <span className="nav-label">
                <span className="nav-title">{item.label}</span>
                <span className="nav-desc">{item.desc}</span>
              </span>
            </button>
          ))}
        </nav>
        <div className="sidebar-foot">
          <span className="demo-dot" />
          演示站点 · 内置虚构人格
        </div>
      </aside>

      <div className="app-shell">
        {/* 移动端：顶部标题栏（品牌名，页面名由底部导航标识） */}
        <header className="mobile-header">
          <span className="leaf"><LeafIcon size={18} /></span>
          5 年后的我
        </header>

        <main className="app-main">
          {tab === 'chat' && <ChatPage />}
          {tab === 'memory' && <MemoryPage />}
          {tab === 'search' && <SearchPage />}
        </main>

        {/* 移动端：底部导航 */}
        <nav className="bottom-nav">
          {NAV_ITEMS.map((item) => (
            <button
              key={item.key}
              className={`bottom-nav-item ${tab === item.key ? 'active' : ''}`}
              onClick={() => setTab(item.key)}
            >
              <NavIcon name={item.key} />
              <span>{item.label}</span>
            </button>
          ))}
        </nav>
      </div>
    </div>
  )
}

export default App
