import { useEffect, useRef, useState } from 'react'
import { chatStream } from '../api'

type Msg = { role: 'user' | 'ai'; content: string }

export default function ChatPage() {
  const [messages, setMessages] = useState<Msg[]>([])
  const [input, setInput] = useState('')
  const [convId, setConvId] = useState<string | null>(null)
  const [streaming, setStreaming] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const send = async () => {
    const text = input.trim()
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

  return (
    <div className="chat-page">
      <div className="chat-messages">
        {messages.length === 0 && (
          <div className="empty-hint">
            <h2>和「5 年后的我」聊聊</h2>
            <p>这里不是附和你的对话框，是一个更成熟的视角。<br />讲讲你最近在纠结什么。</p>
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
          <button className="btn-send" onClick={send} disabled={streaming || !input.trim()}>
            {streaming ? '生成中…' : '发送'}
          </button>
        </div>
      </div>
    </div>
  )
}
