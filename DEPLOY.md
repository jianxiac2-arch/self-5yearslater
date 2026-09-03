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
EMBEDDING_API_URL           https://api.siliconflow.cn/v1/embeddings
EMBEDDING_API_KEY           你的硅基流动 API key（注意：DeepSeek 不提供 embedding，需单独在 siliconflow.cn 注册申请，免费额度即可）
EMBEDDING_API_MODEL         BAAI/bge-m3
DB_PATH                     /data/memory.db
CHROMA_PATH                 /data/chroma
FRONTEND_ORIGIN             https://你的vercel域名.vercel.app
ACCESS_CODE                 你设定的访问口令（如 5yl-demo-2026）
SEED_DEMO_DATA              true
```

**两个公网必填项**：
- `ACCESS_CODE`：防止陌生人拿到链接后盗用你的 DeepSeek 额度、读写记忆库。前端打开时需输入同一口令（口令写进简历/GitHub README，如"访问口令：5yl-demo-2026"）。
- `SEED_DEMO_DATA=true`：首次部署自动写入虚构演示人格（秋招求职者「小林」，仅职业/学业向），评审打开即有记忆和画像效果，不会看到空白应用。对话页底部可"恢复演示数据"一键清空访客内容。

> 成本提示：Railway 已无永久免费层，新账户有试用额度，之后 Hobby 计划约 $5/月；Vercel 免费额度足够；DeepSeek API 费用极低（演示用量每月几毛到几元人民币）。

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

## 二B、备选：Render 免费层部署后端（不想用 Railway 时）

Railway 已无永久免费层；Render 免费层（2026 年仍提供）可长期使用：512MB RAM / 0.1 vCPU、750 实例小时/月（单服务 24/7 = 744h，刚好够）、500 构建分钟/月、5GB 带宽/月。

### 1. 创建 Web Service

1. 注册 https://render.com （GitHub OAuth 登录）并授权访问仓库
2. Dashboard → **New + → Web Service** → 选仓库
3. 配置：
   - **Root Directory**: `backend`
   - **Runtime**: Python 3
   - **Build Command**: `pip install -r requirements.txt`（无 torch，构建快）
   - **Start Command**: `python -m app.seed && uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Instance Type**: Free

### 2. 环境变量

与 Railway 清单基本一致，**不设 DB_PATH / CHROMA_PATH**（免费层无持久盘，用容器内临时目录）：

```
PYTHON_VERSION              3.12.6
DEEPSEEK_API_KEY            你的 deepseek API key
DEEPSEEK_BASE_URL           https://api.deepseek.com
CHAT_MODEL                  deepseek-chat
EMBEDDING_API_URL           https://api.siliconflow.cn/v1/embeddings
EMBEDDING_API_KEY           你的硅基流动 API key（注意：DeepSeek 不提供 embedding，需单独在 siliconflow.cn 注册申请，免费额度即可）
EMBEDDING_API_MODEL         BAAI/bge-m3
FRONTEND_ORIGIN             https://你的vercel域名.vercel.app
ACCESS_CODE                 你设定的访问口令
SEED_DEMO_DATA              true
```

### 3. 免费层的两个特性与应对

| 特性 | 影响 | 应对 |
|---|---|---|
| 15 分钟无流量休眠，冷启动约 1 分钟 | 评审首次打开慢 | cron-job.org（免费）每 14 分钟 ping 一次 `https://xxx.onrender.com/health` 保活；744 < 750h，单服务 24/7 不超限 |
| 临时文件系统（重启丢文件） | 访客聊天记录、数据库不持久 | `SEED_DEMO_DATA=true` 使每次启动自动重建框架 + 演示人格——等于自动恢复演示状态，正是 demo 需要的行为 |

### 4. 验证

访问 `https://你的服务名.onrender.com/health` 应返回 `{"status":"ok"}`。前端 Vercel 配置不变（`VITE_API_BASE=https://你的服务名.onrender.com/api`）。

> 若 Render 注册要求绑定支付方式而你不便绑定：备选 Koyeb（koyeb.com，免费 web service 一个，GitHub 部署，无需信用卡），步骤同上、界面不同。

---

## 三、验证

1. 访问 Vercel 前端 URL，应出现访问口令页；输入 `ACCESS_CODE` 后进入
2. 发一条消息（或点引导话题），确认 AI 能正常流式回复
3. 打开记忆库页，应能看到预置的演示人格（画像/事实/反思）
4. 打开搜索总结页，搜"秋招"或"焦虑"，确认能召回演示记忆
5. 不点口令直接访问后端 API（如 `/api/memory/profile`）应返回 401
6. 对话页点"恢复演示数据"，页面刷新后记忆库回到初始状态

**建议同时录一条 1-2 分钟的演示视频备用**（录屏：输入口令 → 点"实习没用"话题展示反谄媚 → 记忆库页展示分层记忆 → 搜索总结）。简历放"在线 Demo + 口令 + 视频链接"，评审只有 2 分钟时视频比裸链接更稳。

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
| Embedding 报错 | DeepSeek 不提供 embedding 服务 | 用硅基流动（siliconflow.cn，OpenAI 兼容）申请 key，设 EMBEDDING_API_URL / EMBEDDING_API_KEY / EMBEDDING_API_MODEL 三项 |
| CORS 错误 | FRONTEND_ORIGIN 未更新 | Railway 更新后 Redeploy |
| 数据丢失 | 未挂载 Volume | Railway Storage 挂载 `/data` |
| 首条对话慢 | ChromaDB 首次初始化 | 正常，后续会快 |

---

## 六、简历链接

部署完成后，你的简历可以放：
- **在线 Demo**: `https://5yl.vercel.app`
- **GitHub**: `https://github.com/你的用户名/self-5yearslater`

建议在 GitHub README 加一张架构图和截图。
