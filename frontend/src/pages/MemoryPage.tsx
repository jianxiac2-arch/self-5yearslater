import { useEffect, useState } from 'react'
import {
  getProfile, setProfile, deleteProfile,
  listFacts, addFact, deleteFact,
  listPreferences, addPreference, deletePreference,
  listEpisodes, listReflections, listFrameworks,
} from '../api'

type Profile = Record<string, any>
type FactItem = { id: string; category: string; content: string; importance: number }
type PrefItem = { id: string; type: string; content: string; importance: number }
type Episode = { id: string; summary: string; occurred_at?: string }
type Reflection = { id: string; type: string; content: string }
type Framework = { id: string; type: string; name: string; content: string; trigger_conditions: string }

const FACT_CATEGORIES = ['identity', 'work', 'relation', 'goal', 'other']
const PREF_TYPES = ['like', 'dislike', 'style', 'taboo']

export default function MemoryPage() {
  // L1 画像
  const [profile, setProfileState] = useState<Profile>({})
  const [pKey, setPKey] = useState('')
  const [pVal, setPVal] = useState('')

  // L2 事实
  const [facts, setFacts] = useState<FactItem[]>([])
  const [fCat, setFCat] = useState(FACT_CATEGORIES[0])
  const [fContent, setFContent] = useState('')

  // L3 偏好
  const [prefs, setPrefs] = useState<PrefItem[]>([])
  const [prefType, setPrefType] = useState(PREF_TYPES[0])
  const [prefContent, setPrefContent] = useState('')

  // L4-L6 只读
  const [episodes, setEpisodes] = useState<Episode[]>([])
  const [reflections, setReflections] = useState<Reflection[]>([])
  const [frameworks, setFrameworks] = useState<Framework[]>([])

  const loadAll = async () => {
    const [p, f, pr, ep, rf, fw] = await Promise.all([
      getProfile(), listFacts(), listPreferences(), listEpisodes(), listReflections(), listFrameworks(),
    ])
    setProfileState(p)
    setFacts(f)
    setPrefs(pr)
    setEpisodes(ep)
    setReflections(rf)
    setFrameworks(fw)
  }

  useEffect(() => { loadAll() }, [])

  // L1 操作
  const saveProfile = async () => {
    if (!pKey.trim() || !pVal.trim()) return
    await setProfile(pKey.trim(), pVal.trim())
    setPKey(''); setPVal('')
    setProfileState(await getProfile())
  }
  const removeProfile = async (k: string) => {
    await deleteProfile(k)
    setProfileState(await getProfile())
  }

  // L2 操作
  const saveFact = async () => {
    if (!fContent.trim()) return
    await addFact(fCat, fContent.trim())
    setFContent('')
    setFacts(await listFacts())
  }
  const removeFact = async (id: string) => {
    await deleteFact(id)
    setFacts(await listFacts())
  }

  // L3 操作
  const savePref = async () => {
    if (!prefContent.trim()) return
    await addPreference(prefType, prefContent.trim())
    setPrefContent('')
    setPrefs(await listPreferences())
  }
  const removePref = async (id: string) => {
    await deletePreference(id)
    setPrefs(await listPreferences())
  }

  const frameworkLabel: Record<string, string> = {
    thinking_tool: '思维工具',
    population_profile: '人群画像',
    decision_framework: '决策框架',
  }

  return (
    <div className="manage-page">
      <h1 className="page-title">记忆库管理</h1>

      {/* L1 用户画像 */}
      <section className="section">
        <div className="section-title">L1 · 用户画像</div>
        <div className="row">
          <input placeholder="键（如 age、personality、city）" value={pKey} onChange={(e) => setPKey(e.target.value)} />
          <input placeholder="值" value={pVal} onChange={(e) => setPVal(e.target.value)} />
          <button className="btn" onClick={saveProfile}>添加</button>
        </div>
        {Object.keys(profile).length === 0 ? (
          <div className="empty">还没有画像信息。</div>
        ) : (
          Object.entries(profile).map(([k, v]) => (
            <div className="list-item" key={k}>
              <div className="content">
                <strong>{k}</strong>：{String(v)}
              </div>
              <button className="btn-sm btn-danger" onClick={() => removeProfile(k)}>删除</button>
            </div>
          ))
        )}
      </section>

      {/* L2 关键事实 */}
      <section className="section">
        <div className="section-title">L2 · 关键事实</div>
        <div className="row">
          <select value={fCat} onChange={(e) => setFCat(e.target.value)}>
            {FACT_CATEGORIES.map((c) => <option key={c} value={c}>{c}</option>)}
          </select>
          <input placeholder="事实内容" value={fContent} onChange={(e) => setFContent(e.target.value)} />
          <button className="btn" onClick={saveFact}>添加</button>
        </div>
        {facts.length === 0 ? (
          <div className="empty">还没有记录的事实。</div>
        ) : (
          facts.map((f) => (
            <div className="list-item" key={f.id}>
              <div className="content">
                <span className="tag">{f.category}</span>
                {f.content}
                <div className="meta">重要度 {f.importance}</div>
              </div>
              <button className="btn-sm btn-danger" onClick={() => removeFact(f.id)}>删除</button>
            </div>
          ))
        )}
      </section>

      {/* L3 偏好 */}
      <section className="section">
        <div className="section-title">L3 · 偏好</div>
        <div className="row">
          <select value={prefType} onChange={(e) => setPrefType(e.target.value)}>
            {PREF_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
          </select>
          <input placeholder="偏好内容" value={prefContent} onChange={(e) => setPrefContent(e.target.value)} />
          <button className="btn" onClick={savePref}>添加</button>
        </div>
        {prefs.length === 0 ? (
          <div className="empty">还没有记录的偏好。</div>
        ) : (
          prefs.map((p) => (
            <div className="list-item" key={p.id}>
              <div className="content">
                <span className="tag">{p.type}</span>
                {p.content}
              </div>
              <button className="btn-sm btn-danger" onClick={() => removePref(p.id)}>删除</button>
            </div>
          ))
        )}
      </section>

      {/* L4 事件 */}
      <section className="section">
        <div className="section-title">L4 · 事件（对话自动记录）</div>
        {episodes.length === 0 ? (
          <div className="empty">还没有事件。聊几句就会自动产生。</div>
        ) : (
          episodes.map((e) => (
            <div className="list-item" key={e.id}>
              <div className="content">
                {e.summary}
                {e.occurred_at && <div className="meta">{e.occurred_at}</div>}
              </div>
            </div>
          ))
        )}
      </section>

      {/* L5 反思 */}
      <section className="section">
        <div className="section-title">L5 · 反思（搜索总结页可生成）</div>
        {reflections.length === 0 ? (
          <div className="empty">还没有反思记录。</div>
        ) : (
          reflections.map((r) => (
            <div className="list-item" key={r.id}>
              <div className="content">
                <span className="tag">{r.type}</span>
                {r.content}
              </div>
            </div>
          ))
        )}
      </section>

      {/* L6 框架 */}
      <section className="section">
        <div className="section-title">L6 · 认知框架（预置，只读）</div>
        {frameworks.length === 0 ? (
          <div className="empty">框架未初始化，请运行 <code>python -m app.seed</code>。</div>
        ) : (
          frameworks.map((fw) => (
            <div className="list-item" key={fw.id}>
              <div className="content">
                <span className="tag">{frameworkLabel[fw.type] || fw.type}</span>
                <strong>{fw.name}</strong>
                <div className="meta">{fw.trigger_conditions}</div>
              </div>
            </div>
          ))
        )}
      </section>
    </div>
  )
}
