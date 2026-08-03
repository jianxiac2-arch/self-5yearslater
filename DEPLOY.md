# 部署指南：Railway（后端）+ Vercel（前端）

## 架构

```
用户浏览器 → Vercel 前端（React SPA）→ Railway 后端（FastAPI）→ DeepSeek API
                                          ↘ ChromaDB（向量库）+ SQLite（结构化存储）
                                          ↘ DeepSeek Embedding API（生产环境）
```

## 一、Railway 部署后端

### 1. 创建 Railway 项目

1. 注册 https://railway.app （支持 GitHub OAuth）
2. 点击 **New Project** → **Deploy from GitHub repo** → 选你的仓库
3. 进入项目后，删除自动创建的服务（因为 Nixpacks 可能选错）

### 2. 新建后端服务

1. 点击 **+ New** → **Deploy from GitHub repo** → 选你的仓库
2. 在 **Service Details** 里：
   - **Service name**: `5yl-backend`
   - **Root Directory**: `backend`（重要！指向 backend 目录）
3. Railway 会自动检测 Python 项目，读取 `railway.json` 的配置

### 3. 挂载持久化存储

1. 进入 `5yl-backend` 服务 → **Settings** → **Storage**
2. 点击 **+ Add Volume**，挂载路径填 `/data`
3. 这样 ChromaDB 和 SQLite 数据就持久化了

### 4. 设置环境变量

进入 **Settings** → **Variables**，逐个添加：

```
DEEPSEEK_API_KEY            你的 deepseek API key
DEEPSEEK_BASE_URL           https://api.deepseek.com
CHAT_MODEL                  deepseek-chat
EMBEDDING_API_URL           https://api.deepseek.com/v1/embeddings
EMBEDDING_API_KEY           你的 deepseek API key
EMBEDDING_API_MODEL         text-embedding-v1
DB_PATH                     /data/memory.db
CHROMA_PATH                 /data/chroma
FRONTEND_ORIGIN             https://你的vercel域名.vercel.app
```

### 5. 部署

Railway 会自动触发部署（或点击 **Redeploy**）。等待状态变为 **Live**。

健康检查：访问 `https://5yl-backend.up.railway.app/health`，应返回 `{"status":"ok"}`。

**记下后端 URL**，后面配置 Vercel 要用。

---

## 二、Vercel 部署前端

### 1. 创建 Vercel 项目

1. 注册 https://vercel.com （支持 GitHub OAuth）
2. 点击 **Add New Project** → 选你的 GitHub 仓库
3. **Configure Project** 页面：
   - **Framework Preset**: Vite（自动检测）
   - **Root Directory**: `frontend`（重要！指向 frontend 目录）

### 2. 设置环境变量

在 **Project Settings** → **Environment Variables** 添加：

```
VITE_API_BASE    https://5yl-backend.up.railway.app/api
```

**Environment** 勾选全部（Production + Preview + Development）。

### 3. 部署

点击 **Deploy**，等待构建完成。

构建日志应显示：
```
✓ 20 modules transformed.
dist/index.html                   0.45 kB
dist/assets/index-CL3ZQUWt.css    5.48 kB
dist/assets/index-CvZ46_a_.js   204.02 kB
✓ built in 1.38s
```

**记下前端 URL**（如 `https://5yl.vercel.app`）。

### 4. 回到 Railway 更新 CORS

把 Vercel 域名填到 Railway 的 `FRONTEND_ORIGIN` 环境变量，然后 Redeploy。

---

## 三、验证

1. 访问 Vercel 前端 URL
2. 发一条消息，确认 AI 能正常回复
3. 打开记忆库页，确认没有报错
4. 打开搜索总结页，确认能正常搜索

---

## 四、更新代码后的部署

- **Railway**: push 到 GitHub 后自动部署（如果没触发，手动 Redeploy）
- **Vercel**: push 到 GitHub 后自动部署
- **数据**: Railway Volume 中的数据不会因重新部署而丢失

---

## 五、常见问题

| 问题 | 原因 | 解决 |
|------|------|------|
| 前端空白/404 | Root Directory 没设对 | Vercel 设置 Root Directory 为 `frontend` |
| 后端启动失败 | DeepSeek API Key 未配置 | Railway Variables 添加 `DEEPSEEK_API_KEY` |
| Embedding 报错 | EMBEDDING_API_URL 未设置 | Railway Variables 添加 |
| CORS 错误 | FRONTEND_ORIGIN 未更新 | Railway 更新后 Redeploy |
| 数据丢失 | 未挂载 Volume | Railway Storage 挂载 `/data` |
| 首条对话慢 | ChromaDB 首次初始化 | 正常，后续会快 |

---

## 六、简历链接

部署完成后，你的简历可以放：
- **在线 Demo**: `https://5yl.vercel.app`
- **GitHub**: `https://github.com/你的用户名/self-5yearslater`

建议在 GitHub README 加一张架构图和截图。
