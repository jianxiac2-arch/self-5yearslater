/** API 封装：与后端 FastAPI 通信。
 *
 * 开发环境：Vite proxy 转发 /api → localhost:8000（相对路径）
 * 生产环境：设 VITE_API_BASE=https://your-backend.up.railway.app（完整 URL）
 */

const BASE = import.meta.env.VITE_API_BASE || '/api';

// ===== 对话（SSE 流式） =====

export async function chatStream(
  message: string,
  conversationId: string | null,
  onDelta: (delta: string) => void,
  onConversationId: (id: string) => void,
): Promise<void> {
  const resp = await fetch(`${BASE}/chat/stream`, {
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
  const r = await fetch(`${BASE}/chat/conversations`);
  return r.json();
}

export async function getMessages(conversationId: string) {
  const r = await fetch(`${BASE}/chat/conversations/${conversationId}/messages`);
  return r.json();
}

// ===== L1 用户画像 =====

export async function getProfile(): Promise<Record<string, any>> {
  const r = await fetch(`${BASE}/memory/profile`);
  return r.json();
}

export async function setProfile(key: string, value: string) {
  await fetch(`${BASE}/memory/profile`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ key, value, source: 'manual' }),
  });
}

export async function deleteProfile(key: string) {
  await fetch(`${BASE}/memory/profile/${key}`, { method: 'DELETE' });
}

// ===== L2 关键事实 =====

export async function listFacts(category?: string) {
  const url = category ? `${BASE}/memory/facts?category=${category}` : `${BASE}/memory/facts`;
  const r = await fetch(url);
  return r.json();
}

export async function addFact(category: string, content: string, importance = 0.5) {
  const r = await fetch(`${BASE}/memory/facts`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ id: '', category, content, importance, source: 'manual' }),
  });
  return r.json();
}

export async function deleteFact(id: string) {
  await fetch(`${BASE}/memory/facts/${id}`, { method: 'DELETE' });
}

// ===== L3 偏好 =====

export async function listPreferences(type?: string) {
  const url = type ? `${BASE}/memory/preferences?type=${type}` : `${BASE}/memory/preferences`;
  const r = await fetch(url);
  return r.json();
}

export async function addPreference(type: string, content: string, importance = 0.5) {
  await fetch(`${BASE}/memory/preferences`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ id: '', type, content, importance }),
  });
}

export async function deletePreference(id: string) {
  await fetch(`${BASE}/memory/preferences/${id}`, { method: 'DELETE' });
}

// ===== L4 事件 / L5 反思 / L6 框架 =====

export async function listEpisodes(limit = 50) {
  const r = await fetch(`${BASE}/memory/episodes?limit=${limit}`);
  return r.json();
}

export async function listReflections() {
  const r = await fetch(`${BASE}/memory/reflections`);
  return r.json();
}

export async function listFrameworks() {
  const r = await fetch(`${BASE}/memory/frameworks`);
  return r.json();
}

// ===== 元认知：搜索 / 总结 =====

export async function search(query: string, layers: string[] = []) {
  const r = await fetch(`${BASE}/meta/search`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, layers, limit: 10 }),
  });
  return r.json();
}

export async function summarize(dimension: string, value: string, saveAsReflection = false) {
  const r = await fetch(`${BASE}/meta/summary`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ dimension, value, save_as_reflection: saveAsReflection }),
  });
  return r.json();
}
