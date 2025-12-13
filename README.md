# My Coach - AI 私教应用

一个基于 AI 的个人健身教练应用，帮助你制定科学的训练计划并跟踪训练记录。

## 技术栈

- **React 18** - UI 框架
- **Vite 5** - 构建工具
- **TypeScript** - 类型安全
- **React Router 6** - 路由管理
- **Zustand** - 状态管理
- **Sass** - 样式预处理

## 功能特性

- 🏋️ **AI 训练计划生成** - 根据你的个人情况生成 4 周训练计划
- 📝 **训练记录** - 记录每次训练的数据
- 🤖 **AI 运动分析** - 让 AI 教练点评你的训练
- 📅 **日历导出** - 将训练计划导出为 ICS 文件
- ⚙️ **灵活配置** - 支持多种 AI 模型提供商

## 快速开始

### 安装依赖

```bash
npm install
```

### 启动开发服务器

```bash
npm run dev
```

应用将在 http://localhost:3000 启动

### 构建生产版本

```bash
npm run build
```

### 预览生产版本

```bash
npm run preview
```

## 配置 AI 模型

应用支持以下 AI 模型提供商：

1. **OpenAI** (GPT-4/3.5)
2. **DeepSeek** (深度求索)
3. **Anthropic** (Claude)
4. **自定义 API** - 任何 OpenAI 兼容的 API

在「设置」页面配置你的 API Key 和模型选项。

### 关于 CORS

由于浏览器端直接调用 AI API 可能遇到跨域问题，建议：

1. 使用支持 CORS 的代理服务
2. 部署自己的后端中转服务
3. 使用本地代理工具（如开发时使用 Vite 代理）

## 项目结构

```
src/
├── App.tsx              # 应用入口，路由配置
├── App.scss             # 应用容器样式
├── main.tsx             # React 挂载入口
├── app.scss             # 全局样式
├── pages/
│   ├── plan/            # 训练计划页面
│   │   ├── index.tsx
│   │   └── questionnaire/  # 问卷调查
│   ├── record/          # 训练记录页面
│   │   ├── index.tsx
│   │   └── form/        # 记录表单
│   └── settings/        # 设置页面
├── store/               # Zustand 状态管理
│   ├── usePlanStore.ts
│   ├── useRecordStore.ts
│   └── useSettingsStore.ts
├── services/
│   └── ai/              # AI 服务
│       ├── client.ts    # API 客户端
│       ├── index.ts     # 计划生成服务
│       ├── prompts.ts   # 提示词模板
│       └── types.ts     # 类型定义
├── constants/           # 常量配置
└── utils/               # 工具函数
    ├── calendar.ts      # ICS 日历生成
    └── ui.ts            # UI 交互工具
```

## 数据存储

所有数据（训练计划、记录、设置）都保存在浏览器的 localStorage 中，不会上传到任何服务器。

## License

MIT
