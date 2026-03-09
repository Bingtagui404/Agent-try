# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

这是一个手写的 ReAct Agent 命令行工具，是 12 周 AI Agent 开源破局路线的第一周产出物。项目名称暂定 `react-agent`，后续会演化为完整的 `RepoAgent`（一个能对代码仓库执行"读代码→定位问题→修改→跑测试→生成补丁"闭环的 AI Agent）。

当前阶段目标：**用裸 SDK 手写一个 50-100 行的 ReAct Agent**，不使用任何框架（禁止 LangChain、LangGraph、CrewAI 等），推送到 GitHub。

## 核心设计原则

- **铁律一：手写优先，框架在后。** 第一周必须用裸 SDK 纯手写，哪怕只有 50 行代码。目的是真正理解 ReAct 循环的本质，而不是调库。
- **铁律二：每一天的产出都必须被 GitHub 记录。** 从第一天起就 `git init`，每天都 push。绿色的 contribution graph 本身就是简历。
- **手写 ReAct 的目的：** 让模型自主决定何时调用工具。遇到问题时能区分是 Prompt 的问题还是框架逻辑的问题，而手写 50-100 行代码才能真正建立这个判断力。

## 技术约束

- **语言：** Python 3.9+
- **包管理：** uv（不用 pip / conda）
- **LLM SDK：** zhipuai（智谱 GLM-4-Flash，免费模型）。也可选 anthropic SDK，但需要单独的 API Key 和付费额度。
- **禁止使用的框架：** LangChain、LangGraph、CrewAI、AutoGen 或任何 Agent 框架。本周的目标就是不用框架。
- **代码行数：** 50-100 行（不含注释和空行），保持极简。

## ReAct 模式说明

ReAct = Reasoning + Acting。核心是一个 while 循环：

1. 用户提问 → 发送给 LLM（附带可用工具列表）
2. LLM 思考后决定：直接回答 or 调用工具
3. 如果 LLM 选择调用工具 → 本地执行工具函数 → 将结果回传给 LLM → 回到第 2 步
4. 如果 LLM 选择直接回答 → 输出最终结果 → 循环结束

循环控制的关键字段：`finish_reason`（智谱/OpenAI 格式）或 `stop_reason`（Anthropic 格式）。值为 `"tool_calls"` / `"tool_use"` 时继续循环，值为 `"stop"` / `"end_turn"` 时退出。

## 工具设计

需要给 Agent 至少两个简单工具，让它自主决定何时调用：

- `calculate`：计算数学表达式
- `get_weather`：查询天气（可用假数据模拟，也可接真实 API）

工具定义格式遵循 OpenAI 兼容格式（智谱使用此格式）：`{"type": "function", "function": {"name": ..., "description": ..., "parameters": {...}}}`。

## 文件结构

```
react-agent/
├── CLAUDE.md          # 本文件，项目上下文
├── README.md          # 项目说明（动机、架构图、运行步骤）
├── pyproject.toml     # uv 生成的依赖管理文件
├── agent.py           # ReAct Agent 核心代码（50-100 行）
└── .env.example       # 环境变量模板（ZHIPUAI_API_KEY=your-key-here）
```

## 常用命令

```bash
# 创建虚拟环境并安装依赖
uv sync

# 运行 Agent
uv run python agent.py

# 运行测试
uv run pytest tests/

# 运行单个测试
uv run pytest tests/test_xxx.py::test_function_name -v
```

## 本周并行任务（非代码）

- 通读 mini-swe-agent 源码（github.com/SWE-agent/mini-swe-agent，仅 100 行），用半天时间理解"极简 Agent 能做到什么程度"（SWE-Bench 验证集 74%+）。
- 完成 firstcontributions.github.io 教程（约 15 分钟），熟悉 fork → branch → PR 的标准开源工作流。
- 从第二梯队项目（OpenHands / MCP Python SDK / LangGraph / Dify / smolagents）中选 1 个最短的 issue，提交人生第一个 PR 草案。

## 本周交付物

1. GitHub 上可见的 `agent.py`（50-100 行，能跑通的 ReAct Agent）
2. 第一个开源 PR 草案（哪怕是 draft 状态）

## 后续演化方向（本周不做，仅作参考）

- 第 2-3 周：引入 LangGraph 做可控编排（create_react_agent、interrupt、checkpoint）
- 第 3-4 周：学 MCP，用 FastMCP 写一个 MCP Server
- 第 6-7 周：前端面板（WebSocket + 流式输出 + diff 渲染）
- 最终形态：RepoAgent，一个全栈 Agent 产品（Python 后端 + Web 前端 + MCP 工具层）
