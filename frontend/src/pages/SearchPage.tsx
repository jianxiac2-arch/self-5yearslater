import { useState } from 'react'
import { search, summarize } from '../api'

type Hit = { layer: string; id: string; content: string; score?: number }

const LAYERS = [
  { key: 'profile', label: '画像' },
  { key: 'facts', label: '事实' },
  { key: 'preferences', label: '偏好' },
  { key: 'episodes', label: '事件' },
  { key: 'reflections', label: '反思' },
  { key: 'frameworks', label: '框架' },
]

const DIMENSIONS = [
  { key: 'time', label: '按时间', placeholder: '如：过去一个月 / 最近一周' },
  { key: 'topic', label: '按主题', placeholder: '如：职业选择、学习计划' },
  { key: 'person', label: '按人物', placeholder: '某个人名' },
]

const layerLabel: Record<string, string> = {
  profile: '画像',
  facts: '事实',
  preferences: '偏好',
  episodes: '事件',
  reflections: '反思',
  frameworks: '框架',
}

export default function SearchPage() {
  // 搜索
  const [query, setQuery] = useState('')
  const [selectedLayers, setSelectedLayers] = useState<string[]>([])
  const [hits, setHits] = useState<Hit[]>([])
  const [searching, setSearching] = useState(false)
  const [searched, setSearched] = useState(false)

  // 总结
  const [dim, setDim] = useState('time')
  const [dimVal, setDimVal] = useState('')
  const [saveReflection, setSaveReflection] = useState(false)
  const [summary, setSummary] = useState('')
  const [summarizing, setSummarizing] = useState(false)

  const toggleLayer = (k: string) => {
    setSelectedLayers((prev) => prev.includes(k) ? prev.filter((x) => x !== k) : [...prev, k])
  }

  const doSearch = async () => {
    const q = query.trim()
    if (!q) return
    setSearching(true)
    setSearched(true)
    try {
      const r = await search(q, selectedLayers)
      setHits(r.hits || [])
    } catch (e) {
      setHits([])
      console.error(e)
    } finally {
      setSearching(false)
    }
  }

  const doSummarize = async () => {
    const v = dimVal.trim()
    if (!v) return
    setSummarizing(true)
    setSummary('')
    try {
      const r = await summarize(dim, v, saveReflection)
      setSummary(r.summary || '')
      if (r.reflection_id) setSummary((s) => s + `\n\n[已存为反思 ${r.reflection_id}]`)
    } catch (e) {
      setSummary(`[出错: ${(e as Error).message}]`)
    } finally {
      setSummarizing(false)
    }
  }

  const currentDim = DIMENSIONS.find((d) => d.key === dim)!

  return (
    <div className="manage-page">
      <h1 className="page-title">元认知：搜索与总结</h1>

      {/* 搜索 */}
      <section className="section">
        <div className="section-title">语义搜索记忆</div>
        <div className="row">
          <input
            placeholder="搜索你说过的话、记录的事…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && doSearch()}
          />
          <button className="btn" onClick={doSearch} disabled={searching || !query.trim()}>
            {searching ? '搜索中…' : '搜索'}
          </button>
        </div>
        <div className="row" style={{ flexWrap: 'wrap' }}>
          {LAYERS.map((l) => (
            <label key={l.key} style={{ display: 'flex', gap: 4, alignItems: 'center', fontSize: 13 }}>
              <input
                type="checkbox"
                checked={selectedLayers.includes(l.key)}
                onChange={() => toggleLayer(l.key)}
              />
              {l.label}
            </label>
          ))}
          <span style={{ fontSize: 12, color: 'var(--color-text-muted)' }}>不选则搜全部层</span>
        </div>
        {searched && (
          hits.length === 0 ? (
            <div className="empty">没有找到相关记忆。</div>
          ) : (
            hits.map((h, i) => (
              <div className="list-item" key={i}>
                <div className="content">
                  <span className="tag">{layerLabel[h.layer] || h.layer}</span>
                  {h.content}
                  {h.score != null && <div className="meta">相似度 {h.score.toFixed(3)}</div>}
                </div>
              </div>
            ))
          )
        )}
      </section>

      {/* 总结 */}
      <section className="section">
        <div className="section-title">总结记忆</div>
        <div className="row">
          <select value={dim} onChange={(e) => setDim(e.target.value)} style={{ flex: '0 0 120px' }}>
            {DIMENSIONS.map((d) => <option key={d.key} value={d.key}>{d.label}</option>)}
          </select>
          <input
            placeholder={currentDim.placeholder}
            value={dimVal}
            onChange={(e) => setDimVal(e.target.value)}
          />
          <button className="btn" onClick={doSummarize} disabled={summarizing || !dimVal.trim()}>
            {summarizing ? '总结中…' : '总结'}
          </button>
        </div>
        <label style={{ display: 'flex', gap: 6, alignItems: 'center', fontSize: 13, color: 'var(--color-text-secondary)' }}>
          <input type="checkbox" checked={saveReflection} onChange={(e) => setSaveReflection(e.target.checked)} />
          存为反思（L5）
        </label>
        {summary && (
          <div className="list-item">
            <div className="content" style={{ whiteSpace: 'pre-wrap' }}>{summary}</div>
          </div>
        )}
      </section>
    </div>
  )
}
