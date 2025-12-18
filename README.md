# MyCoach - AI 私人健身教练

基于 AI 的个人健身教练应用，为用户提供科学、个性化的训练计划和运动分析。

## 架构概览

```
myCoach/
├── frontend/                 # React 前端应用
│   ├── src/
│   │   ├── services/api/     # 后端 API 调用层
│   │   ├── services/intervals/ # Intervals.icu 客户端
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
├── server/                   # Node.js Intervals 集成服务
│   ├── routes/               # API 路由
│   ├── services/             # 业务逻辑
│   ├── db/                   # SQLite 数据库
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
- **Intervals.icu 同步**：自动从 Intervals.icu 导入骑行、跑步、游泳等运动数据

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
- Intervals 集成服务：http://localhost:3001
- PostgreSQL：localhost:5433

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

## Intervals.icu 数据同步配置

MyCoach 支持从 [Intervals.icu](https://intervals.icu) 自动同步运动数据。Intervals.icu 是一个强大的训练分析平台，可以从 Garmin、Strava、Wahoo 等设备/平台自动导入数据。

### 获取 Intervals.icu API Key

1. 登录 [Intervals.icu](https://intervals.icu)
2. 进入 **Settings** → **Developer Settings**
3. 点击 **Create API Key** 生成一个新的 API Key
4. 复制生成的 API Key（格式类似 `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`）

### 方式一：通过 Web UI 配置（推荐）

1. 访问 MyCoach 应用：http://localhost:3000
2. 进入 **设置** 页面
3. 在 **Intervals.icu 数据同步** 区域填写：
   - **API Key**：粘贴你的 Intervals.icu API Key
   - **Athlete ID**（可选）：留空则自动获取
   - **Webhook Secret**（可选）：用于实时同步验证
4. 点击 **连接 Intervals.icu** 按钮
5. 连接成功后，可以选择同步天数并点击 **立即同步**

### 方式二：通过环境变量配置

在 `.env` 文件中添加：

```bash
# Intervals.icu 配置
INTERVALS_API_KEY=your_intervals_api_key
INTERVALS_ATHLETE_ID=i12345    # 可选，留空则自动获取
INTERVALS_WEBHOOK_SECRET=your_secret   # 可选，用于实时同步
```

### 配置实时同步（Webhook）

如果希望在 Intervals.icu 上有新活动时自动同步到 MyCoach：

1. 在 Intervals.icu 进入 **Settings** → **Developer Settings**
2. 在 **Webhooks** 区域添加新的 Webhook：
   - **URL**: `https://your-domain.com/webhook/intervals`
   - **Secret**: 自定义一个密钥字符串
3. 在 MyCoach 中配置相同的 Webhook Secret

> **注意**：Webhook 需要公网可访问的 URL。本地开发时可使用 ngrok 等工具。

### 支持的运动类型

从 Intervals.icu 同步的运动将自动映射到 MyCoach 的运动类型：

| Intervals.icu | MyCoach |
|---------------|---------|
| Ride, VirtualRide | 骑行 |
| Run, VirtualRun | 跑步 |
| Swim | 游泳 |
| WeightTraining, Workout | 力量训练 |
| Yoga | 瑜伽 |
| HIIT | HIIT |
| 其他 | 其他 |

### Intervals API 端点

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | /api/intervals/config | 获取配置状态 |
| PUT | /api/intervals/config | 保存配置 |
| DELETE | /api/intervals/config | 断开连接 |
| POST | /api/intervals/test | 测试连接 |
| POST | /api/intervals/sync | 手动同步活动 |
| GET | /api/intervals/records | 获取已同步记录 |
| POST | /webhook/intervals | Webhook 接收端点 |

### 安全说明

- **API Key 仅存储在服务器端**：不会暴露给前端浏览器
- **Webhook 验证**：支持 Secret 验证，防止伪造请求
- **日志脱敏**：API Key 不会出现在日志中
- **HTTPS**：生产环境建议配置 SSL/TLS

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！
