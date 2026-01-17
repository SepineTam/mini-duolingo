# mini-duolingo
A mini-duolingo by vibe-coding. 

## Quickly Start
```bash
git clone https://github.com/sepinetam/mini-duolingo
uv sync
cp .env.example .env
```

使用你的 `API_KEY` 去替换 `.env` 文件中的 `API_KEY`
```dotenv
# 默认使用DeepSeek作为Model Provider
OPENAI_API_KEY=<YOU_OPENAI_API_KEY>
OPENAI_BASE_URL=https://api.deepseek.com/v1
OPENAI_MODEL=deepseek-chat
```

启动你的项目
```bash
uv run main.py
```

## 项目简介

这是一个轻量级的AI驱动的语言学习平台，参考 Duolingo 的核心功能。

**核心特点**：
- **AI 自动生成题库**：使用 AI 根据学习内容自动生成多种题型（单选、多选、填空等）
- **智能复习算法**：基于 SuperMemo-2 的间隔重复算法，根据用户答题表现动态调整复习时间
- **互动学习体验**：提供 Quiz（测验）、Review（复习）、Feedback（反馈）等多个模块
- **现代化技术栈**：Flask 后端 + H5 前端 + Tailwind CSS 样式


