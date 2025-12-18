# MyCoach - AI 私人健身教练

基于 AI 的个人健身教练应用，为用户提供科学、个性化的训练计划和运动分析。

## 架构概览

```
myCoach/
├── frontend/                 # React 前端应用
│   ├── src/
│   │   ├── services/api/     # 后端 API 调用层
│   │   ├── store/            # Zustand 状态管理
│   │   ├── pages/            # 页面组件
│   │   └── utils/            # 工具函数
│   └── Dockerfile
├── backend/                  # FastAPI 后端服务
│   ├── app/
│   │   ├── api/              # REST API 端点
│   │   ├── services/ai/      # AI Provider Adapter
│   │   ├── prompts/          # Prompt 模板
│   │   ├── models/           # SQLAlchemy 数据模型
│   │   └── core/             # 配置、日志、数据库
│   └── Dockerfile
├── docker-compose.yml        # Docker 一键部署
└── env.example               # 环境变量示例
```

## 功能特性

- **智能训练计划生成**：基于用户问卷，AI 生成个性化的 4 周周期化训练计划
- **运动记录追踪**：记录每次训练，支持专业数据（间歇、配速等）
- **AI 教练分析**：智能分析训练表现，提供专业建议
- **计划动态调整**：基于训练记录，AI 自动调整后续计划
- **自然语言对话**：通过对话方式灵活修改训练计划

## 技术栈

### 前端
- React 18 + TypeScript
- Vite 构建工具
- Zustand 状态管理
- SCSS 样式

### 后端
- Python FastAPI
- SQLAlchemy (async)
- PostgreSQL 数据库
- AI Provider Adapter (支持 OpenAI, DeepSeek, Claude)

### 部署
- Docker + Docker Compose
- Nginx 反向代理

## 快速开始

### 1. 克隆项目

```bash
git clone <repository-url>
cd myCoach
```

### 2. 配置环境变量

```bash
cp env.example .env
# 编辑 .env 文件，填入你的 AI API Key
```

### 3. 使用 Docker Compose 启动

```bash
docker compose up -d
```

服务将在以下端口启动：
- 前端：http://localhost:3000
- 后端 API：http://localhost:8000
- PostgreSQL：localhost:5432

### 4. 访问应用

打开浏览器访问 http://localhost:3000

## 开发模式

### 后端开发

```bash
cd backend
pip install -r requirements.txt

# 设置环境变量
export DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/mycoach
export AI_API_KEY=your_api_key

# 启动开发服务器
uvicorn app.main:app --reload --port 8000
```

### 前端开发

```bash
cd frontend
npm install
npm run dev
```

前端开发服务器会自动代理 API 请求到后端。

## API 端点

### 训练计划

| 方法 | 路径 | 描述 |
|------|------|------|
| POST | /api/plans/generate | 生成训练计划 |
| GET | /api/plans | 获取计划列表 |
| GET | /api/plans/{id} | 获取单个计划 |
| PUT | /api/plans/{id} | 更新计划 |
| DELETE | /api/plans/{id} | 删除计划 |
| POST | /api/plans/{id}/chat | 对话调整计划 |
| POST | /api/plans/{id}/update | 基于记录更新计划 |

### 运动记录

| 方法 | 路径 | 描述 |
|------|------|------|
| POST | /api/records | 创建记录 |
| GET | /api/records | 获取记录列表 |
| DELETE | /api/records/{id} | 删除记录 |
| POST | /api/records/{id}/analyze | AI 分析记录 |

## 安全性

- **前端不接触敏感信息**：API Key、Prompt 模板等全部由后端管理
- **日志脱敏**：后端日志不记录 API Key 和完整 Prompt 内容
- **环境变量配置**：所有敏感配置通过环境变量注入
- **数据库隔离**：PostgreSQL 仅内网访问

## AI Provider 配置

支持多种 AI 提供商，通过环境变量配置：

```bash
# OpenAI (默认)
AI_PROVIDER=openai
AI_API_KEY=sk-xxx

# DeepSeek
AI_PROVIDER=deepseek
AI_API_KEY=sk-xxx

# Claude
AI_PROVIDER=claude
AI_API_KEY=sk-xxx

# 自定义 OpenAI 兼容 API
AI_PROVIDER=openai
AI_BASE_URL=https://your-proxy.com/v1
AI_MODEL=gpt-4o
AI_API_KEY=your_key
```

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！
