# Mini-Duolingo 产品需求文档 (PRD) v1.0

## 1. 项目概述

### 1.1 项目定位
一个轻量级的AI驱动语言学习应用，专注于词汇学习，通过AI动态生成题目和个性化推荐，提供高效的学习体验。

### 1.2 核心特性
- **AI驱动内容生成**：题目、翻译、判题全部由AI实时生成
- **无感知学习体验**：启动即学，无需手动选择
- **智能复习系统**：基于SM-2算法的间隔重复学习
- **个性化难度调整**：根据用户特征（词汇量等）动态调整

### 1.3 技术栈
- **后端**：Flask (Python)
- **前端**：H5 + Tailwind CSS
- **数据存储**：CSV文件
- **AI能力**：大语言模型（待定）

---

## 2. 核心功能

### 2.1 词汇练习
- 从用户收集的文章中提取词汇
- 每次练习15道题目，覆盖3-5个核心单词
- 题目之间强关联，确保深度学习
- 题型：单选题（单词↔释义）、填空题

### 2.2 智能复习
- 基于SM-2算法的间隔重复系统
- 自动判断今日是否需要复习
- 复习算法支持热插拔

### 2.3 即时反馈
- 每道题答完即时显示对错
- 可选查看AI解析
- 必须全部答对才能结束练习

### 2.4 进度追踪
- 记录每次练习的详细数据
- 追踪单词掌握程度
- 统计学习历史

---

## 3. 用户流程

### 3.1 启动流程
```
用户打开应用
  ↓
系统分析：检查今日是否有待复习单词
  ↓
├─ 有待复习 → 进入复习模式
└─ 无待复习 → 进入学习模式（随机选择文章）
  ↓
AI生成15道题目（基于文章 + user.md用户特征）
  ↓
开始答题
```

### 3.2 练习流程
```
显示题目（第X题/共15题）
  ↓
用户答题
  ↓
即时反馈（对/错 + 正确答案）
  ↓
[可选] 点击查看AI解析
  ↓
下一题
  ↓
15题完成后检查是否全部答对
  ↓
├─ 有错题 → 重做错题（直到全对）
└─ 全部正确 → 进入结束界面
```

### 3.3 结束界面
- 本次练习统计（答对X题，正确率X%）
- 学习的单词列表
- 查看错题（可选）

---

## 4. 数据结构设计

### 4.1 CSV文件结构

#### 4.1.1 user_profile.csv - 用户基本信息
| 字段 | 类型 | 说明 |
|------|------|------|
| user_id | string | 用户唯一标识 |
| vocabulary_level | int | 词汇量等级（1-10） |
| preferred_language | string | 偏好学习的语言 |
| total_practice_count | int | 总练习次数 |
| total_words_learned | int | 总学习单词数 |
| created_at | datetime | 创建时间 |
| last_practice | datetime | 最后练习时间 |

#### 4.1.2 practice_history.csv - 练习会话记录
| 字段 | 类型 | 说明 |
|------|------|------|
| practice_id | string | 练习唯一标识 |
| timestamp | datetime | 时间戳 |
| source_article | string | 来源文章 |
| words_learned | string | 本次学习的单词列表（JSON） |
| question_count | int | 题目数量 |
| correct_count | int | 答对数量 |
| accuracy | float | 正确率 |
| difficulty | int | 难度等级 |
| time_spent | int | 耗时（秒） |

#### 4.1.3 question_history.csv - 题目详细记录
| 字段 | 类型 | 说明 |
|------|------|------|
| question_id | string | 题目唯一标识 |
| practice_id | string | 所属练习会话 |
| timestamp | datetime | 时间戳 |
| question_type | string | 题型（单选/填空） |
| word | string | 涉及的单词 |
| question_content | string | 题目内容 |
| correct_answer | string | 正确答案 |
| user_answer | string | 用户答案 |
| is_correct | boolean | 是否正确 |
| difficulty | int | 难度等级 |

#### 4.1.4 word_progress.csv - 单词掌握情况
| 字段 | 类型 | 说明 |
|------|------|------|
| word | string | 单词 |
| language | string | 语言 |
| total_attempts | int | 总练习次数 |
| correct_attempts | int | 答对次数 |
| last_review | datetime | 最后复习时间 |
| next_review | datetime | 下次复习时间 |
| ease_factor | float | 轻松度因子（SM-2算法） |
| interval | int | 复习间隔（天） |
| mastery_level | float | 掌握程度（0-1） |

### 4.2 配置文件

#### 4.2.1 user.md - 用户特征配置
```markdown
# 用户特征

- 词汇量等级: 5
- 学习语言: 英语
- 学习目标: 日常交流
- 偏好题型: 单选为主，填空为辅
- 每日学习时长: 15分钟
```

---

## 5. 技术架构

### 5.1 系统架构
```
┌─────────────────────────────────────────┐
│              Frontend (H5)              │
│        (Tailwind CSS + Vanilla JS)      │
└─────────────────┬───────────────────────┘
                  │ HTTP API
┌─────────────────┴───────────────────────┐
│           Backend (Flask)               │
│  ┌─────────────┬─────────────┐         │
│  │  题目生成   │  复习策略   │         │
│  │  (AI驱动)   │  (SM-2)     │         │
│  └──────┬──────┴──────┬──────┘         │
│         │             │                │
│  ┌──────┴──────┬──────┴──────┐         │
│  │  数据存储   │  AI接口     │         │
│  │  (CSV)      │  (LLM)      │         │
│  └─────────────┴─────────────┘         │
└─────────────────────────────────────────┘
```

### 5.2 核心模块

#### 5.2.1 题目生成模块 (question_generator.py)
- 从文章中提取词汇
- 根据用户特征生成题目
- 确保题目间关联性

#### 5.2.2 复习策略模块 (review_strategy.py)
- SM-2算法实现
- 判断今日待复习单词
- 支持热插拔接口

#### 5.2.3 数据管理模块 (data_manager.py)
- CSV读写操作
- 用户信息管理
- 历史记录查询

#### 5.2.4 AI接口模块 (ai_service.py)
- 题目生成
- 翻译服务
- 答案判题
- 题目解析

### 5.3 目录结构
```
mini-duolingo/
├── articles/              # 学习文章存放目录
│   └── example.txt
├── data/                  # CSV数据文件
│   ├── user_profile.csv
│   ├── practice_history.csv
│   ├── question_history.csv
│   └── word_progress.csv
├── src/                   # 源代码
│   ├── app.py            # Flask主应用
│   ├── question_generator.py
│   ├── review_strategy.py
│   ├── data_manager.py
│   └── ai_service.py
├── templates/             # 前端模板
│   ├── index.html        # 练习页面
│   └── result.html       # 结束页面
├── user.md               # 用户特征配置
└── main.py               # 启动脚本
```

---

## 6. 开发计划

### 6.1 Phase 1: MVP核心功能
- [ ] 搭建Flask框架
- [ ] 实现CSV数据存储
- [ ] 实现题目生成模块（AI驱动）
- [ ] 实现基础答题界面（单选+填空）
- [ ] 实现即时反馈和结束界面

### 6.2 Phase 2: 智能复习
- [ ] 实现SM-2复习算法
- [ ] 实现自动判断复习/学习模式
- [ ] 实现错题重做机制

### 6.3 Phase 3: AI增强
- [ ] 接入真实AI API（待确定）
- [ ] 实现题目解析功能
- [ ] 优化题目质量（关联性、难度适配）

### 6.4 Phase 4: 优化迭代
- [ ] UI/UX优化
- [ ] 性能优化
- [ ] 根据使用反馈调整

---

## 7. 待定事项

- [ ] AI模型选择（OpenAI / Claude / 本地模型）
- [ ] 题目质量评估标准
- [ ] 词汇量等级如何量化
- [ ] 文章内容类型建议

---

## 8. 风险与挑战

### 8.1 技术风险
- AI生成题目的稳定性和质量
- SM-2算法参数调优
- CSV数据量增大后的性能

### 8.2 用户体验风险
- 题目难度不适配
- AI生成题目重复或无关联
- 复习频率不合理

---

## 9. 成功指标

- 用户能完成一次完整的15题练习
- 题目之间具有明显关联性
- 复习算法能有效提醒复习
- AI生成题目可用率 > 90%

---

*PRD版本: v1.0*
*创建日期: 2026-01-17*
*最后更新: 2026-01-17*
