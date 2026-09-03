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

type LayerKey = 'profile' | 'facts' | 'prefs' | 'episodes' | 'reflections' | 'frameworks'

const LAYERS: { key: LayerKey; label: string; hint: string }[] = [
  { key: 'profile', label: 'L1 画像', hint: '你是谁：身份、性格、目标' },
  { key: 'facts', label: 'L2 事实', hint: '发生过什么、有什么能力' },
  { key: 'prefs', label: 'L3 偏好', hint: '喜欢什么、忌讳什么' },
  { key: 'episodes', label: 'L4 事件', hint: '对话中自动记录的经历' },
  { key: 'reflections', label: 'L5 反思', hint: '从轨迹中提炼的模式与趋势' },
  { key: 'frameworks', label: 'L6 框架', hint: '预置的思维工具，只读' },
]

const FACT_CATEGORIES = ['identity', 'career', 'work', 'relation', 'goal', 'event', 'personality', 'other']
const PREF_TYPES = ['like', 'dislike', 'style', 'taboo']

const FACT_CATEGORY_LABELS: Record<string, string> = {
  identity: '身份', career: '职业', work: '工作', relation: '关系',
  goal: '目标', event: '事件', personality: '性格', other: '其他',
}
const PREF_TYPE_LABELS: Record<string, string> = {
  like: '喜欢', dislike: '不喜欢', style: '风格', taboo: '忌讳',
}
const REFLECTION_TYPE_LABELS: Record<string, string> = {
  pattern: '模式', trend: '趋势', summary: '总结',
}
const FRAMEWORK_TYPE_LABELS: Record<string, string> = {
  thinking_tool: '思维工具', population_profile: '人群画像', decision_framework: '决策框架',
}

const DEMO_MARKER_KEY = '_demo_seed_version'

export default function MemoryPage() {
  // 当前分层
  const [layer, setLayer] = useState<LayerKey>('profile')

  // L1 画像
  const [profile, setProfileState] = useState<Profile>({})
  const [pKey, setPKey] = useState('')
  const [pVal, setPVal] = useState('')

  // L2 事实
  const [facts, setFacts] = useState<FactItem[]>([])
  const [fCat, setFCat] = useState(FACT_CATEGORIES[0])
  const [fContent, setFContent] = useState('')
  const [factFilter, setFactFilter] = useState<string | null>(null)

  // L3 偏好
  const [prefs, setPrefs] = useState<PrefItem[]>([])
  const [prefType, setPrefType] = useState(PREF_TYPES[0])
  const [prefContent, setPrefContent] = useState('')
  const [prefFilter, setPrefFilter] = useState<string | null>(null)

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

  // 画像展示：过滤掉种子版本标记；「数据说明」放到脚注
  const profileEntries = Object.entries(profile).filter(([k]) => k !== DEMO_MARKER_KEY && k !== '数据说明')
  const profileNote = profile['数据说明'] as string | undefined

  const factCats = Array.from(new Set(facts.map((f) => f.category)))
  const filteredFacts = factFilter ? facts.filter((f) => f.category === factFilter) : facts
  const prefTypes = Array.from(new Set(prefs.map((p) => p.type)))
  const filteredPrefs = prefFilter ? prefs.filter((p) => p.type === prefFilter) : prefs

  const counts: Record<LayerKey, number> = {
    profile: profileEntries.length,
    facts: facts.length,
    prefs: prefs.length,
    episodes: episodes.length,
    reflections: reflections.length,
    frameworks: frameworks.length,
  }

  const currentLayer = LAYERS.find((l) => l.key === layer)!

  return (
    <div className="manage-page">
      <header className="page-head">
        <h1 className="page-title">记忆库</h1>
        <p className="page-sub">
          演示人格「小林」（虚构）的分层记忆 · L4 事件由对话自动产生，L5 反思可在「搜索总结」页生成
        </p>
      </header>

      {/* 分层导航 */}
      <div className="layer-tabs">
        {LAYERS.map((l) => (
          <button
            key={l.key}
            className={`layer-tab ${layer === l.key ? 'active' : ''}`}
            onClick={() => setLayer(l.key)}
          >
            {l.label}
            <span className="layer-count">{counts[l.key]}</span>
          </button>
        ))}
      </div>

      <section className="section">
        <div className="section-title">
          {currentLayer.label.replace(/^(L\d)\s/, '$1 · ')}
          <span className="section-hint">{currentLayer.hint}</span>
        </div>

        {/* ===== L1 画像 ===== */}
        {layer === 'profile' && (
          <>
            <div className="add-form">
              <input placeholder="键（如 city、personality）" value={pKey} onChange={(e) => setPKey(e.target.value)} />
              <input placeholder="值" value={pVal} onChange={(e) => setPVal(e.target.value)} />
              <button className="btn" onClick={saveProfile}>添加</button>
            </div>
            {profileEntries.length === 0 ? (
              <div className="empty">还没有画像信息。</div>
            ) : (
              <div className="kv-grid">
                {profileEntries.map(([k, v]) => (
                  <div className="kv-card" key={k}>
                    <div className="kv-head">
                      <span className="kv-key">{k}</span>
                      <button className="icon-btn" onClick={() => removeProfile(k)} title="删除">✕</button>
                    </div>
                    <div className="kv-val">{String(v)}</div>
                  </div>
                ))}
              </div>
            )}
            {profileNote && <div className="foot-note">{profileNote}</div>}
          </>
        )}

        {/* ===== L2 事实 ===== */}
        {layer === 'facts' && (
          <>
            <div className="add-form">
              <select value={fCat} onChange={(e) => setFCat(e.target.value)}>
                {FACT_CATEGORIES.map((c) => <option key={c} value={c}>{FACT_CATEGORY_LABELS[c] || c}</option>)}
              </select>
              <input placeholder="事实内容" value={fContent} onChange={(e) => setFContent(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && saveFact()} />
              <button className="btn" onClick={saveFact}>添加</button>
            </div>
            {factCats.length > 0 && (
              <div className="filter-chips">
                <button className={`f-chip ${factFilter === null ? 'active' : ''}`} onClick={() => setFactFilter(null)}>全部</button>
                {factCats.map((c) => (
                  <button key={c} className={`f-chip ${factFilter === c ? 'active' : ''}`} onClick={() => setFactFilter(c)}>
                    {FACT_CATEGORY_LABELS[c] || c}
                  </button>
                ))}
              </div>
            )}
            {filteredFacts.length === 0 ? (
              <div className="empty">还没有记录的事实。</div>
            ) : (
              filteredFacts.map((f) => (
                <div className="card" key={f.id}>
                  <div className="card-main">
                    <div className="card-top">
                      <span className="tag">{FACT_CATEGORY_LABELS[f.category] || f.category}</span>
                      <span className="importance" title={`重要度 ${f.importance}`}>
                        <span className="importance-bar">
                          <span style={{ width: `${Math.round((f.importance || 0) * 100)}%` }} />
                        </span>
                      </span>
                    </div>
                    <div className="card-content">{f.content}</div>
                  </div>
                  <button className="icon-btn" onClick={() => removeFact(f.id)} title="删除">✕</button>
                </div>
              ))
            )}
          </>
        )}

        {/* ===== L3 偏好 ===== */}
        {layer === 'prefs' && (
          <>
            <div className="add-form">
              <select value={prefType} onChange={(e) => setPrefType(e.target.value)}>
                {PREF_TYPES.map((t) => <option key={t} value={t}>{PREF_TYPE_LABELS[t] || t}</option>)}
              </select>
              <input placeholder="偏好内容" value={prefContent} onChange={(e) => setPrefContent(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && savePref()} />
              <button className="btn" onClick={savePref}>添加</button>
            </div>
            {prefTypes.length > 0 && (
              <div className="filter-chips">
                <button className={`f-chip ${prefFilter === null ? 'active' : ''}`} onClick={() => setPrefFilter(null)}>全部</button>
                {prefTypes.map((t) => (
                  <button key={t} className={`f-chip ${prefFilter === t ? 'active' : ''}`} onClick={() => setPrefFilter(t)}>
                    {PREF_TYPE_LABELS[t] || t}
                  </button>
                ))}
              </div>
            )}
            {filteredPrefs.length === 0 ? (
              <div className="empty">还没有记录的偏好。</div>
            ) : (
              filteredPrefs.map((p) => (
                <div className="card" key={p.id}>
                  <div className="card-main">
                    <div className="card-top">
                      <span className="tag">{PREF_TYPE_LABELS[p.type] || p.type}</span>
                    </div>
                    <div className="card-content">{p.content}</div>
                  </div>
                  <button className="icon-btn" onClick={() => removePref(p.id)} title="删除">✕</button>
                </div>
              ))
            )}
          </>
        )}

        {/* ===== L4 事件 ===== */}
        {layer === 'episodes' && (
          episodes.length === 0 ? (
            <div className="empty">还没有事件。聊几句就会自动产生。</div>
          ) : (
            <div className="timeline">
              {episodes.map((e) => (
                <div className="tl-item" key={e.id}>
                  <div className="tl-dot" />
                  <div className="tl-body">
                    <div className="tl-content">{e.summary}</div>
                    {e.occurred_at && <div className="meta">{e.occurred_at}</div>}
                  </div>
                </div>
              ))}
            </div>
          )
        )}

        {/* ===== L5 反思 ===== */}
        {layer === 'reflections' && (
          reflections.length === 0 ? (
            <div className="empty">还没有反思记录。</div>
          ) : (
            reflections.map((r) => (
              <div className="card" key={r.id}>
                <div className="card-main">
                  <div className="card-top">
                    <span className="tag">{REFLECTION_TYPE_LABELS[r.type] || r.type}</span>
                  </div>
                  <div className="card-content">{r.content}</div>
                </div>
              </div>
            ))
          )
        )}

        {/* ===== L6 框架 ===== */}
        {layer === 'frameworks' && (
          frameworks.length === 0 ? (
            <div className="empty">框架未初始化，请运行 <code>python -m app.seed</code>。</div>
          ) : (
            frameworks.map((fw) => (
              <div className="card" key={fw.id}>
                <div className="card-main">
                  <div className="card-top">
                    <span className="tag">{FRAMEWORK_TYPE_LABELS[fw.type] || fw.type}</span>
                    <strong>{fw.name}</strong>
                  </div>
                  <div className="card-content">{fw.content}</div>
                  {fw.trigger_conditions && <div className="meta">触发：{fw.trigger_conditions}</div>}
                </div>
              </div>
            ))
          )
        )}
      </section>
    </div>
  )
}
