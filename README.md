# Clocktower Agent

一个面向 **Blood on the Clocktower（血染钟楼）DM / Storyteller（说书人）** 的主持辅助 Agent 原型。

本项目支持：

- 根据玩家人数与角色池自动组板
- 为邪恶阵营推荐可伪装的镇民角色
- 根据当前局势判断哪些角色技能可以发动
- 根据局中状态为 DM 提供平衡性辅助建议
- 支持 DM 通过自然语言指令直接更新游戏状态

---

##  核心设计理念

### 三层架构


DM输入（自然语言）
↓
LLM解析（指令层）
↓
game_state.json（唯一真实状态）
↓
技能判断 + DM建议（执行层）


---

### 关键原则

-  LLM 不直接控制游戏
-  JSON 是唯一真实状态
-  所有修改必须可追踪、可复现

---
---

## 1. 项目结构

```text
clocktower_agent/
├── main.py
├── README.md
├── tests/
│   └── test_main_flow.py
├── data/
│   ├── roles.json
│   ├── game_state.json
│   ├── generated_board.json
│   ├── recommended_bluffs.json
│   ├── skill_status.json
│   └── dm_advice.json
└── core/
    ├── board_rules.py
    ├── role_loader.py
    ├── llm_client.py
    ├── prompts.py
    ├── board_builder.py
    └── balance_checker.py
```

## 2. 环境要求

```text
Python 3.10+

macOS / Linux / Windows

Ollama（本地大模型运行）

推荐模型：qwen2.5:3b
```

## 3. 安装步骤
```text
1️⃣ 安装 Ollama
brew install ollama

启动服务：

ollama serve

⚠️ 必须保持运行！

2️⃣ 下载模型
ollama pull qwen2.5:3b
3️⃣ 测试模型
ollama run qwen2.5:3b

退出：

/bye
4️⃣ Python 环境

```

## 4. 数据文件说明
```text
1. data/game_state.json（最重要）

2. DM 主要操作文件

包含：

当前模式（setup / runtime）

当前是第几夜/第几天

谁活着谁死了

谁摆烂（drunk）

哪些技能已使用

3. data/roles.json

角色库定义：

阵营

技能描述

适用人数

4.  自动生成文件
文件	作用
generated_board.json	当前板子
recommended_bluffs.json	坏人伪装建议
skill_status.json	技能可用情况
dm_advice.json	DM建议

5. game_state.json 示例
{
  "mode": "runtime",
  "num_players": 8,
  "phase": "night",
  "night_number": 2,

  "alive_players": ["A","B","C","D","E","F","G"],
  "dead_players": ["H"],

  "drunk_players": ["A"],
  "used_once_skills": ["Help Session"]
}
```

## 5. 运行流程
```text
🎬 开局（Setup）
"mode": "setup"

运行：

python3 main.py

输出：

板子（generated_board.json）

Bluff 推荐

🎮 局中（Runtime）
"mode": "runtime"

运行：

python3 main.py

输出：

技能判断

DM 建议
```
## 6.  CLI 交互
```text
启动后进入：

> 
可用命令
命令	作用
show	查看当前状态
setup	重新生成板子
analyze	分析当前局势
command	输入自然语言
save	保存状态
quit	退出

```
## 7. 自然语言指令（核心能力）
```text
输入：

进入第3夜
A 摆烂
H 死亡
Help Session 已使用

系统自动修改： game_state.json
```
## 8. 测试
```text
运行：

python3 -m unittest discover -s tests -v
```
测试覆盖：

· Setup 是否生成合法板子

· Runtime 是否正常分析

· 技能判断逻辑

· DM建议输出

## 9. 当前能力

· 自动组板
· 技能发动判断
·Bluff推荐
· DM辅助
· 指令驱动状态更新

## 10. 当前限制

部分角色技能仍为手写规则

夜晚顺序未实现

部分技能未拆分（once / each night）

LLM建议仍可能偏泛

## 11. 作者

Guojing Wang
