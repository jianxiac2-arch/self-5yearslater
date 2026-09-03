/** API 封装：与后端 FastAPI 通信。
 *
 * 开发环境：Vite proxy 转发 /api → localhost:8000（相对路径）
 * 生产环境：设 VITE_API_BASE=https://your-backend.up.railway.app（完整 URL）
 *
 * 公网部署：后端可设 ACCESS_CODE，前端把口令存 localStorage，
 * 所有请求带 X-Access-Code 头；401 时清口令并广播 auth:failed 事件。
 */

const BASE = import.meta.env.VITE_API_BASE || '/api';

// ===== 访问口令 =====

const ACCESS_CODE_KEY = '5yl_access_code';

export function getAccessCode(): string {
  return localStorage.getItem(ACCESS_CODE_KEY) || '';
}

export function setAccessCode(code: string) {
  localStorage.setItem(ACCESS_CODE_KEY, code.trim());
}

export function clearAccessCode() {
  localStorage.removeItem(ACCESS_CODE_KEY);
}

function authHeaders(extra?: Record<string, string>): Record<string, string> {
  const h: Record<string, string> = { ...(extra || {}) };
  const code = getAccessCode();
  if (code) h['X-Access-Code'] = code;
  return h;
}

async function apiFetch(url: string, options: RequestInit = {}): Promise<Response> {
  const resp = await fetch(url, {
    ...options,
    headers: authHeaders(options.headers as Record<string, string> | undefined),
  });
  if (resp.status === 401) {
    clearAccessCode();
    window.dispatchEvent(new Event('auth:failed'));
    throw new Error('访问口令无效或缺失');
  }
  return resp;
}

export async function authStatusRequired(): Promise<boolean> {
  // 探测接口本身豁免口令，不走 apiFetch
  const r = await fetch(`${BASE}/auth/status`);
  if (!r.ok) return false;
  const data = await r.json();
  return !!data.auth_required;
}

export async function resetDemoData() {
  const r = await apiFetch(`${BASE}/admin/reset-demo`, { method: 'POST' });
  if (!r.ok) throw new Error(`重置失败: ${r.status}`);
  return r.json();
}

export async function getMetaInfo() {
  const r = await apiFetch(`${BASE}/meta/info`);
  return r.json();
}

// ===== 对话（SSE 流式） =====

export async function chatStream(
  message: string,
  conversationId: string | null,
  onDelta: (delta: string) => void,
  onConversationId: (id: string) => void,
): Promise<void> {
  const resp = await apiFetch(`${BASE}/chat/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, conversation_id: conversationId }),
  });
  if (!resp.ok || !resp.body) throw new Error(`对话请求失败: ${resp.status}`);

  const reader = resp.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() || '';
    for (const line of lines) {
      if (line.startsWith('data: ')) {
        try {
          const obj = JSON.parse(line.slice(6));
          if (obj.conversation_id) onConversationId(obj.conversation_id);
          if (obj.delta) onDelta(obj.delta);
        } catch {
          /* ignore parse error */
        }
      }
    }
  }
}

export async function listConversations() {
  const r = await apiFetch(`${BASE}/chat/conversations`);
  return r.json();
}

export async function getMessages(conversationId: string) {
  const r = await apiFetch(`${BASE}/chat/conversations/${conversationId}/messages`);
  return r.json();
}

// ===== L1 用户画像 =====

export type ProfileEntry = { key: string; value: string; confidence?: number; source?: string; updated_at?: string }
export async function getProfile(): Promise<Record<string, ProfileEntry>> {
  const r = await apiFetch(`${BASE}/memory/profile`);
  return r.json();
}

export async function setProfile(key: string, value: string) {
  await apiFetch(`${BASE}/memory/profile`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ key, value, source: 'manual' }),
  });
}

export async function deleteProfile(key: string) {
  await apiFetch(`${BASE}/memory/profile/${key}`, { method: 'DELETE' });
}

// ===== L2 关键事实 =====

export async function listFacts(category?: string) {
  const url = category ? `${BASE}/memory/facts?category=${category}` : `${BASE}/memory/facts`;
  const r = await apiFetch(url);
  return r.json();
}

export async function addFact(category: string, content: string, importance = 0.5) {
  const r = await apiFetch(`${BASE}/memory/facts`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ id: '', category, content, importance, source: 'manual' }),
  });
  return r.json();
}

export async function deleteFact(id: string) {
  await apiFetch(`${BASE}/memory/facts/${id}`, { method: 'DELETE' });
}

// ===== L3 偏好 =====

export async function listPreferences(type?: string) {
  const url = type ? `${BASE}/memory/preferences?type=${type}` : `${BASE}/memory/preferences`;
  const r = await apiFetch(url);
  return r.json();
}

export async function addPreference(type: string, content: string, importance = 0.5) {
  await apiFetch(`${BASE}/memory/preferences`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ id: '', type, content, importance }),
  });
}

export async function deletePreference(id: string) {
  await apiFetch(`${BASE}/memory/preferences/${id}`, { method: 'DELETE' });
}

// ===== L4 事件 / L5 反思 / L6 框架 =====

export async function listEpisodes(limit = 50) {
  const r = await apiFetch(`${BASE}/memory/episodes?limit=${limit}`);
  return r.json();
}

export async function listReflections() {
  const r = await apiFetch(`${BASE}/memory/reflections`);
  return r.json();
}

export async function listFrameworks() {
  const r = await apiFetch(`${BASE}/memory/frameworks`);
  return r.json();
}

// ===== 元认知：搜索 / 总结 =====

export async function search(query: string, layers: string[] = []) {
  const r = await apiFetch(`${BASE}/meta/search`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, layers, limit: 10 }),
  });
  return r.json();
}

export async function summarize(dimension: string, value: string, saveAsReflection = false) {
  const r = await apiFetch(`${BASE}/meta/summary`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ dimension, value, save_as_reflection: saveAsReflection }),
  });
  return r.json();
}
