# 5 Years Later · 5 年后的我

> 一个具备**元认知**与**独立判断**的个人 AI Agent。不是又一个 ChatBot——它有自己的观点，不会为了谄媚而附和，能用 5 年后的成熟视角给你定制化建议。

## ✨ 核心特性

- **分层记忆库**：L1 用户画像 → L2 关键事实 → L3 偏好 → L4 事件 → L5 反思 → L6 认知框架，结构化存储 + 向量语义检索
- **反谄媚推理**：先独立分析再表达，对就是对，错就是错，不玩"你说得对，但是…"
- **认知框架层**：预置思维工具库（长期主义、二阶效应、机会成本等）+ 29 岁高认知人群参照系，替代传统人设
- **元认知能力**：跨会话语义搜索 + 多维度总结，避免单会话上下文膨胀后"越聊越笨"
- **SSE 流式对话**：打字机效果，实时响应

## 🏗️ 架构

```
用户浏览器 → Vercel 前端（React SPA）→ Railway 后端（FastAPI）→ DeepSeek API
                                          ↘ ChromaDB（向量库）+ SQLite（结构化存储）
                                          ↘ DeepSeek Embedding API（生产环境）
```

### 记忆分层

| 层级 | 名称 | 存储方式 | 说明 |
|------|------|----------|------|
| L1 | 用户画像 | SQLite | 性格、年龄、职业等核心设定 |
| L2 | 关键事实 | SQLite + ChromaDB | 持久化的重要事实 |
| L3 | 偏好 | SQLite | 思维偏好、决策风格 |
| L4 | 事件 | SQLite + ChromaDB | 对话自动产生的事件记录 |
| L5 | 反思 | SQLite + ChromaDB | 总结性的自我洞察 |
| L6 | 认知框架 | ChromaDB（预置） | 思维工具 + 人群画像 + 决策框架 |

### 反谄媚推理流程

```
用户输入 → 独立分析（抛开用户观点）→ 得出结论 → 对比用户观点 → 诚实表达
         ↓                                                    ↓
    调用认知框架                                       认同 or 反对
    检索相关记忆                                       给出依据（框架/事实/权衡）
                                                       提供可落地建议
```

## 🛠️ 技术栈

| 层 | 技术 |
|----|------|
| 后端 | FastAPI · Python 3.12 |
| 前端 | React 19 + TypeScript + Vite |
| 向量库 | ChromaDB |
| 结构化存储 | SQLite |
| LLM | DeepSeek API |
| Embedding | BGE-small-zh（本地）/ DeepSeek Embedding API（生产） |
| 部署 | Railway（后端）+ Vercel（前端）+ Docker |

## 🚀 快速开始

### 本地开发

```bash
# 1. 克隆仓库
git clone https://github.com/jianxiac2-arch/self-5yearslater.git
cd self-5yearslater

# 2. 配置后端环境变量
cp .env.example backend/.env
# 编辑 backend/.env，填入 DEEPSEEK_API_KEY

# 3. 启动后端
cd backend
pip install -r requirements.txt
python -m app.seed          # 初始化认知框架
uvicorn app.main:app --host 0.0.0.0 --port 8000

# 4. 启动前端（新终端）
cd frontend
npm install
npm run dev
# 访问 http://localhost:5173
```

### Docker 部署

```bash
# 一键启动
docker compose up --build
# 前端: http://localhost:5173
# 后端: http://localhost:8000
```

### 生产部署

详见 [DEPLOY.md](DEPLOY.md)（Railway + Vercel 免费托管方案）。

## 📁 项目结构

```
self-5yearslater/
├── backend/
│   ├── app/
│   │   ├── prompts/          # System prompt + 认知框架预置
│   │   ├── routers/          # API 路由（chat / memory / meta）
│   │   ├── services/         # 业务逻辑（对话引擎 / 记忆 / LLM / 元认知）
│   │   ├── config.py         # 全局配置
│   │   ├── database.py       # SQLAlchemy 模型
│   │   ├── vector_store.py   # ChromaDB 封装
│   │   └── seed.py           # 认知框架初始化
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── pages/            # 对话页 / 记忆库页 / 搜索总结页
│   │   ├── api.ts            # API 封装
│   │   └── index.css         # 浅绿主题样式
│   ├── Dockerfile
│   └── vercel.json
├── .env.example              # 环境变量模板
├── docker-compose.yml
├── railway.json              # Railway 部署配置
└── DEPLOY.md                 # 部署指南
```

## 🎯 核心机制详解

### 认知框架层（L6）

不同于传统 AI 的"人设"，本项目用**认知框架层**作为"5 年后视角"的知识来源：

- **思维工具库**：8 种可调用的思考方式（长期主义、二阶效应、反事实推理、机会成本、逆向思考、系统思考、概率思维、第二层思考）
- **29 岁高认知人群画像**：已识破的认知陷阱、知识结构、价值观光谱
- **决策框架**：通用决策流程（定义问题 → 列出选项 → 5 年后果 → 可逆性检验 → 止损复盘）

这些框架在对话时按语义相关性自动注入 system prompt，作为思考工具使用，而非背诵给用户。

### 反谄媚推理

System prompt 的核心规则：

> 先抛开用户观点独立分析，得出结论后对比——对就是对，错就是错，不要为了"独立"而刻意反对。

避免两个常见陷阱：
1. **先附和再转折**（"你说得对，但是…"）→ 直接表达判断
2. **为反对而反对** → 基于独立分析的诚实表达

### 元认知搜索

跨会话语义搜索 + 多维度总结：
- 按层级搜索（事实/事件/反思/框架）
- 按维度总结（"我最近在纠结什么"→ 提取关键议题 + 建议）
- 搜索结果可存为 L5 反思

## 📝 可定制项

所有"修改口子"都留好了，直接改对应文件后重启即可：

| 想改什么 | 改哪个文件 |
|----------|-----------|
| Agent 的性格/语气/立场 | `backend/app/prompts/system.py` |
| 思维工具/视角内容 | `backend/app/prompts/frameworks.py` |
| 浅绿主题颜色 | `frontend/src/index.css` 顶部 CSS 变量 |
| 模型/API Key | `backend/.env` |

## 🔒 隐私说明

- 所有记忆数据（SQLite + ChromaDB）存储在本地，不对外上传
- Docker 部署时通过 volume 挂载确保数据持久化
- 生产部署用 Railway Volume 持久化数据

## 📄 License

No license — 个人项目，仅供学习和简历展示。
