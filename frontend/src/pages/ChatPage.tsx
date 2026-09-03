import { useEffect, useRef, useState } from 'react'
import { chatStream, resetDemoData } from '../api'

type Msg = { role: 'user' | 'ai'; content: string }

// 引导提问：贴合演示 Case（华生·1920 / 香奈儿·1953 等历史人物虚拟用户），
// 让首次访问的评审 2 分钟内撞到核心卖点：反谄媚 / 分层记忆 / 5 年视角推演。
// 提问风格刻意做成"用户真实在纠结的、值得反谄媚的判断"，不是泛泛而谈。
const SUGGESTED = [
  '我被整个行业拉黑了，中年失业，家人都劝我低头认错求原谅，我该认输吗？',
  '他们都说我年纪太大了，该退休了，再出来会被年轻人笑话，我真的过时了吗？',
  '我犯过一个很大的错，伤害过很多人，这辈子是不是已经没有翻身的机会了？',
  '所有人都走了同一条路，只有我想反着来，我是不是太倔了？',
]

export default function ChatPage() {
  const [messages, setMessages] = useState<Msg[]>([])
  const [input, setInput] = useState('')
  const [convId, setConvId] = useState<string | null>(null)
  const [streaming, setStreaming] = useState(false)
  const [resetting, setResetting] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const send = async (preset?: string) => {
    const text = (preset ?? input).trim()
    if (!text || streaming) return
    setInput('')
    setMessages((prev) => [...prev, { role: 'user', content: text }, { role: 'ai', content: '' }])
    setStreaming(true)
    try {
      await chatStream(
        text,
        convId,
        (delta) => {
          setMessages((prev) => {
            const next = [...prev]
            const last = next[next.length - 1]
            if (last && last.role === 'ai') {
              next[next.length - 1] = { ...last, content: last.content + delta }
            }
            return next
          })
        },
        (id) => setConvId(id),
      )
    } catch (e) {
      setMessages((prev) => {
        const next = [...prev]
        const last = next[next.length - 1]
        if (last && last.role === 'ai') {
          next[next.length - 1] = { ...last, content: last.content + `\n[出错: ${(e as Error).message}]` }
        }
        return next
      })
    } finally {
      setStreaming(false)
      inputRef.current?.focus()
    }
  }

  const onKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      send()
    }
  }

  const onResetDemo = async () => {
    if (resetting) return
    setResetting(true)
    try {
      await resetDemoData()
      window.location.reload()
    } catch {
      alert('重置失败：本实例可能未启用演示数据')
      setResetting(false)
    }
  }

  return (
    <div className="chat-page">
      <div className="chat-messages">
        {messages.length === 0 && (
          <div className="empty-hint">
            <h2>和「5 年后的我」聊聊</h2>
            <p>这里不是附和你的对话框，是一个更成熟的视角。<br />讲讲你最近在纠结什么，或试试下面的话题：</p>
            <div className="chips">
              {SUGGESTED.map((s) => (
                <button key={s} className="chip" onClick={() => void send(s)} disabled={streaming}>
                  {s}
                </button>
              ))}
            </div>
            <button className="reset-demo" onClick={onResetDemo} disabled={resetting}>
              {resetting ? '重置中…' : '↺ 恢复演示数据（清空本次聊天记录）'}
            </button>
          </div>
        )}
        {messages.map((m, i) => (
          <div key={i} className={`msg ${m.role}`}>
            <div className="msg-avatar">{m.role === 'user' ? '我' : '5y'}</div>
            <div className="msg-bubble">
              {m.content || (m.role === 'ai' && streaming ? '…' : '')}
            </div>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>
      <div className="chat-input-area">
        <div className="chat-input-wrap">
          <textarea
            ref={inputRef}
            className="chat-input"
            placeholder="说说最近在纠结什么…（Enter 发送，Shift+Enter 换行）"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={onKeyDown}
            rows={1}
          />
          <button className="btn-send" onClick={() => void send()} disabled={streaming || !input.trim()}>
            {streaming ? '生成中…' : '发送'}
          </button>
        </div>
      </div>
    </div>
  )
}
