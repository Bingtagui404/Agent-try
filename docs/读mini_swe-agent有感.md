# 读 mini-swe-agent 有感

## 一、Agent 的定义与架构

Agent = LLM + Tool + Loop + Memory

- **LLM**：思考、推理、决策
- **工具**：与外部世界交互
- **循环**：控制"想→做→看"的节奏
- **记忆**：保持上下文连贯

最主流的架构：**ReAct**（来自 2022 年普林斯顿 + Google 的论文 *"ReAct: Synergizing Reasoning and Acting in Language Models"*）

```
    ┌─────────┐
    │  任务    │
    └────┬────┘
         ▼
    ┌─────────┐
    │ Thought  │  ← LLM 思考："我应该先看看文件结构"
    │ (推理)    │
    └────┬────┘
         ▼
    ┌─────────┐
    │ Action   │  ← 调用工具：execute("ls -la")
    │ (行动)    │
    └────┬────┘
         ▼
    ┌─────────┐
    │Observation│ ← 看到结果："total 64, src/, README.md..."
    │ (观察)    │
    └────┬────┘
         │
         ▼
    完成了吗？──否──→ 回到 Thought
         │
         是
         ▼
    ┌─────────┐
    │  结果    │
    └─────────┘
```

ReAct 论文的核心洞察：**"想"和"做"是互相增强的**——
- reason to act：思考帮助 LLM 制定计划、分解任务、处理异常
- act to reason：行动的结果为推理提供新信息，修正错误认知

2026 年所有主流 Agent 框架（OpenAI Agents SDK、Google ADK、Anthropic Claude Agent SDK、LangGraph）都是 ReAct 的变体。

## 二、Workflow vs Agent 的区别

**Workflow（工作流）**：
人类预定义好流程，LLM 只是流程中的一个"工人"。
比如：先翻译 → 再总结 → 最后润色。每一步做什么是人写死的。

**Agent（智能体）**：
LLM 自己决定下一步做什么。
比如：给它一个 bug → 它自己决定先看代码还是先跑测试。每一步做什么是 LLM 动态决定的。

```
  Anthropic 的建议：

  先从最简单的方案开始，只在真正需要灵活性时才升级为 Agent。

  简单 ──────────────────────────── 复杂
  单次 LLM      Workflow      Agent
  调用          (预定义流程)   (LLM 自主决策)
```

## 三、我的第一个 Agent（react-agent）

前几天，我第一次在 Claude 的提示下手搓了第一个 Agent。使用了 Anthropic 家的 SDK，第一次在模型和官方 sdk-doc 的帮助下成功连上了智谱的 GLM-4.5-Flash 并在终端进行了第一次对话。

开发过程：
1. 按 SDK 格式定义工具（name、description、input_schema）
2. 模型地址和 API Key 用 dotenv 放入 .env 文件
3. 定义和 LLM 的交互：message 的组成
4. 循环开始：传参数 → 获得回答 → 按 `end_turn` 作为循环终止条件
5. 遍历回复中的 `tool_use` → 接收工具名和参数 → 执行 → 把结果 append 回 messages

**注意**：我的 react-agent 用的是 Anthropic 格式，工具结果用 `role="user"` + `type: "tool_result"` 传回（不是 OpenAI 的 `role="tool"`）。这是 Anthropic API 的标准做法，不是写错了。

## 四、mini-swe-agent 源码阅读笔记

### 4.1 项目定位

mini-swe-agent 是一款面向 **SWE-Bench 评测**的极简 Agent（核心 ~100 行），设计上偏向于用命令行参数批量跑任务（`mini -m gpt-4o -c swebench.yaml`），和 Claude Code、Codex、OpenClaw 等交互式 Coding Agent 侧重点不同。

它在 SWE-Bench Verified 上达到了 **74%+** 的通过率。

### 4.2 整体架构：三层 + 工厂模式 + 配置系统

```
┌─────────────────────────────────────────────────────────┐
│  CLI 入口 (run/mini.py)                                  │
│    typer 解析命令行参数 → 合并配置 → 调用三大工厂函数       │
└────────────────────────┬────────────────────────────────┘
                         │
        ┌────────────────┼────────────────┐
        ▼                ▼                ▼
   get_agent()      get_model()     get_environment()
        │                │                │
        ▼                ▼                ▼
  ┌──────────┐    ┌──────────┐    ┌──────────┐
  │  Agent   │    │  Model   │    │Environment│
  │ 控制循环  │◄──►│ 调 LLM   │    │ 执行命令  │
  └──────────┘    └──────────┘    └──────────┘
```

**三层职责：**
- **Agent 层**（agents/default.py）：控制 Thought→Action→Observation 循环
- **Model 层**（models/litellm_model.py）：调用 LLM、解析动作、格式化观测结果
- **Environment 层**（environments/local.py）：用 subprocess.run 执行 bash 命令

**工厂模式**：三个 `__init__.py` 都用同一套模式——短名称（如 `"default"`）→ 映射字典 → `importlib` 动态导入 → 返回类实例。好处是换组件只改配置，不改代码。

### 4.3 消息流：一次完整的交互

```
1. 初始化 messages 列表：
   messages = [
     {role: "system",  content: 渲染后的 system_template},      ← 告诉 LLM "你是谁"
     {role: "user",    content: 渲染后的 instance_template},     ← 告诉 LLM "你的任务"
   ]
   其中模板用 Jinja2 渲染，{{ task }} 被替换为实际任务描述

2. Agent 调用 Model：
   model.query(messages) → 把完整 messages + tools=[BASH_TOOL] 发给 LLM API
   注意：BASH_TOOL 工具定义是作为 tools 参数单独传的，不在 messages 里面

3. LLM 返回回复：
   {role: "assistant", tool_calls: [{function: {name: "bash", arguments: '{"command":"ls -la"}'}}]}

4. Agent 让 Environment 执行命令：
   env.execute(action) → subprocess.run("ls -la") → 返回 {output: "...", returncode: 0}
   returncode 遵循 Unix 约定：0=成功，非0=失败，-1=Python层面异常

5. Model 格式化观测结果：
   用 observation_template（Jinja2 模板）把命令输出渲染成消息
   如果输出超过 10000 字符：保留前 5000 + 后 5000，中间省略（防止撑爆上下文窗口）

6. 追加到 messages：
   messages.append({role: "tool", tool_call_id: "call_xxx", content: "渲染后的输出"})

7. 回到步骤 2，循环继续
```

### 4.4 两种动作解析模式

mini-swe-agent 支持两种方式从 LLM 回复中提取要执行的命令：

| | 文本模式 (actions_text.py) | tool_call 模式 (actions_toolcall.py) |
|---|---|---|
| 对应 Model 类 | LitellmTextbasedModel | LitellmModel（默认） |
| LLM 返回什么 | 纯文本，命令在 ` ```mswea_bash_command ``` ` 中 | 结构化 tool_calls JSON |
| 怎么提取命令 | 正则表达式扫描 | 直接读 JSON 字段 |
| 每次几条命令 | 强制只能 1 条 | 可以多条 |
| 需要消歧标记？ | 需要（`mswea_bash_command` 防止误匹配示例代码） | 不需要 |
| 观测结果 role | `"user"` | `"tool"` |
| 对应配置文件 | default.yaml（XML 格式输出） | mini.yaml（JSON 格式输出） |

通过 `model_class` 配置项选择模式，不是运行时自动检测。

### 4.5 循环控制与退出机制

整体循环由 `DefaultAgent.run()` 的 `while True` 驱动，核心是 `step() = query() + execute_actions()`。

**退出方式（5 种异常，分两类）**：

可控中断（`InterruptAgentFlow` 子类，不一定退出循环）：
1. **Submitted** ← Agent 执行 `echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT`，表示任务完成（最常见的正常退出）
2. **LimitsExceeded** ← 步数或费用超标
3. **UserInterruption** ← 用户 Ctrl+C 或拒绝执行（**不退出循环**，Agent 可以换方案继续）
4. **FormatError** ← LLM 输出格式不对（**不退出循环**，把纠错提示追加到对话让 LLM 重试）

真正的异常（退出循环并 raise）：
5. **其他 Exception** ← 网络断了、API Key 过期等，记录到轨迹文件后退出

**判断是否退出**：检查最后一条消息的 `role` 是否为 `"exit"`。Submitted 和 LimitsExceeded 的消息带 `role="exit"` 所以会退出；UserInterruption 和 FormatError 不带，所以循环继续。

### 4.6 DefaultAgent vs InteractiveAgent

- **DefaultAgent**：纯自动运行，不和用户交互，适合批量评测
- **InteractiveAgent**：继承 DefaultAgent，增加了确认环节
  - `mode=confirm`：每步执行前问用户"确认执行吗？"
  - `mode=yolo`：跳过确认，全自动（和 DefaultAgent 行为相同）
  - `mode=human`：用户手动输入命令，LLM 不参与

### 4.7 执行环境（7 种）

| 环境 | 执行方式 | 适用场景 |
|------|---------|---------|
| **local** | `subprocess.run(cmd)` 本地执行 | 开发、调试、学习 |
| **docker** | `docker exec 容器 cmd` | 评测（隔离安全） |
| singularity | Singularity 容器 | HPC 集群 |
| swerex_docker | SWE-ReX + Docker | 高级评测 |
| swerex_modal | SWE-ReX + Modal 云 | 大规模并行评测 |
| bubblewrap | Linux 轻量沙箱 | 快速隔离 |
| contree | 容器树状环境 | 复杂挂载策略 |

核心理解 local 和 docker 的区别就够了：本地执行没有隔离（LLM 能碰你所有文件），Docker 执行有隔离（搞坏了删容器重来）。Agent 不需要知道区别——都是调 `env.execute(action)`，多态搞定。

### 4.8 配置系统

```
配置来源（优先级从低到高）：
  default.yaml（基础配置）
      ↓ recursive_merge 递归合并
  mini.yaml / swebench.yaml（场景配置，覆盖部分字段）
      ↓
  CLI key=value（如 -c model.model_kwargs.temperature=0.5）
      ↓
  CLI 参数（如 -m gpt-4o）← 最高优先级
```

关键工具：
- `recursive_merge()`：递归合并字典，嵌套 dict 逐 key 合并而非整体替换
- `UNSET = object()`：哨兵对象，区分"没传值"和"传了 None"
- `get_config_from_spec()`：统一入口，判断输入是文件名还是 key=value 并分别处理

这套配置系统是"软件工程脚手架"，不是 Agent 核心逻辑，理解思路即可。

### 4.9 防御性编程：LLM 可能不听话

prompt 里写了"每次只返回一条命令"，但 tool_call 协议允许 LLM 一次返回多条。prompt 是"建议"（软约束），API 协议是"能力"（硬约束），LLM 不一定遵守建议。

所以代码做了两层防御：

1. **来几条执行几条**：`outputs = [env.execute(action) for action in actions]`，不假设只有一条
2. **补齐未执行的动作**：如果 3 条命令只执行了前 2 条（第 3 条因异常中断），用占位结果补齐到 3 个

```python
# 补齐逻辑
not_executed = {"output": "", "returncode": -1, "exception_info": "action was not executed"}
padded_outputs = outputs + [not_executed] * (len(actions) - len(outputs))
```

为什么必须补齐？因为 OpenAI API 要求**每个 tool_call 都必须有对应的 role="tool" 回复**，少一条就报错。

### 4.10 多模态支持（multimodal_regex）

默认关闭的可选功能。当 Agent 执行的命令输出中包含图片（如 base64 编码的截图），`multimodal_regex` 用正则从输出文本中提取图片，把纯文本消息升级为图文混合消息，让支持多模态的 LLM 能真正"看到"图片。

```
没有 multimodal_regex：
  LLM 看到："data:image/png;base64,iVBOR..."  ← 一串乱码，看不懂

有 multimodal_regex：
  LLM 看到：[文字部分] + [图片]  ← 真正能"看到"图片内容
```

### 4.11 轨迹文件（serialize + save）

Agent 每一步结束后都会通过 `save()` 把完整状态保存为 JSON 文件（`.traj.json`），包含：

- **messages**：完整对话历史（可以回放整个过程）
- **info**：运行统计（费用、调用次数、退出状态、提交结果）
- **config**：使用的配置（方便复现）

保存在 `run()` 的 `finally` 块中，所以**即使中途崩溃也有记录**。这对调试非常关键——你可以打开轨迹文件，看 Agent 第几步开始走偏的。

## 五、mini-swe-agent 与我的 react-agent 对比

| 维度 | mini-swe-agent | 我的 react-agent |
|------|----------------|-----------------|
| 工具 | bash 命令（任意命令） | Python 函数（calculate、get_weather） |
| 安全性 | 依赖外部沙箱（Docker） | 工具白名单天然隔离 |
| 退出机制 | 显式信号（echo COMPLETE_TASK...） | 隐式退出（stop_reason="end_turn"） |
| 动作解析 | 文本模式/tool_call 模式可选 | 纯 tool_call 模式 |
| 工具结果格式 | OpenAI 格式 role="tool" | Anthropic 格式 role="user" + type="tool_result" |
| LLM 接口 | litellm 聚合库（支持所有 LLM） | Anthropic SDK + 智谱兼容接口 |
| 配置 | YAML + recursive_merge + CLI 覆盖 | 硬编码 |
| 代码量 | 核心 ~100 行，完整 ~3000 行 | 目标 50-100 行 |

## 六、横向对比：主流 Coding Agent

| | mini-swe-agent | Claude Code | Codex CLI | OpenCode | OpenClaw |
|---|---|---|---|---|---|
| 语言 | Python | TypeScript | Rust（早期是 TypeScript，2025 年中重写为 Rust） | TypeScript | TypeScript |
| 工具调用模式 | 文本 + tool_call 都支持 | 纯 tool_call | 纯 tool_call | 纯 tool_call | tool_call 为主，文本回退 |
| 退出机制 | 显式信号 | 用户控制 | LLM 隐式停止 | LLM 隐式停止 | LLM 隐式停止 + 600s 超时 |
| 多模型适配 | litellm | 只绑 Anthropic | 只绑 OpenAI | Vercel AI SDK | 自己写适配层 |
| 定位 | 评测/研究 | 交互式编程助手 | 交互式编程助手 | 交互式编程助手 | 多平台 AI 助手 |

## 七、面试要点总结

**必须能回答的问题：**

1. **什么是 AI Agent？** → Agent = LLM + Tool + Loop + Memory，核心架构是 ReAct
2. **ReAct 模式是什么？** → Thought→Action→Observation 交替循环，推理指导行动，行动反馈推理
3. **Agent 怎么决定何时停止？** → 显式信号（特定命令）/ 隐式停止（finish_reason）/ 用户控制
4. **tool_call 和纯文本解析的区别？** → 结构化 JSON vs 正则提取，前者无歧义，后者需要自定义标记消歧
5. **怎么防止 Agent 执行危险命令？** → 容器隔离（Docker）/ 工具白名单 / 用户确认（mode=confirm）
6. **多模型适配怎么做？** → 翻译层（litellm / Vercel AI SDK），写一次代码调所有 LLM
7. **Workflow 和 Agent 的区别？** → Workflow 是预定义流程，Agent 是 LLM 动态决策
