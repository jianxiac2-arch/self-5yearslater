import { useState } from 'react'
import ChatPage from './pages/ChatPage'
import MemoryPage from './pages/MemoryPage'
import SearchPage from './pages/SearchPage'

type Tab = 'chat' | 'memory' | 'search'

function App() {
  const [tab, setTab] = useState<Tab>('chat')

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
