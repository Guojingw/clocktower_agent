import json


def build_board_prompt(grouped_candidates, num_players, rules, theme, difficulty):
    return f"""
你是 Blood on the Clocktower 的剧本设计 Agent。

请根据候选角色池，为一局 {num_players} 人、主题为“{theme}”、难度为“{difficulty}”的游戏配置板子。

规则：
- 镇民 {rules['townsfolk']} 名
- 外来者 {rules['outsiders']} 名
- 爪牙 {rules['minions']} 名
- 恶魔 1 名
- 只能从候选角色中选择
- 不允许重复
- 不允许发明新角色
- 优先选择符合校园/UNSW主题的角色
- 尽量平衡信息、控制、误导、保护能力

只输出 JSON，不要解释，不要 markdown，不要代码块。

格式：
{{
  "townsfolk": ["角色1", "角色2"],
  "outsiders": ["角色3"],
  "minions": ["角色4"],
  "demon": "角色5",
  "reasoning": "一句简短说明"
}}

候选角色池：
{json.dumps(grouped_candidates, ensure_ascii=False)}
"""


def build_bluff_prompt(board):
    return f"""
你是 Blood on the Clocktower 的邪恶阵营辅助工具。

当前板子：
{json.dumps(board, ensure_ascii=False)}

请为邪恶阵营推荐 3 个适合伪装成的镇民角色。

要求：
- 必须从当前板子的镇民列表中选择
- 不允许重复
- 尽量选择容易伪装、信息不容易被立即验证的角色
- 只输出 JSON，不要解释

格式：
{{
  "bluffs": ["角色1", "角色2", "角色3"]
}}
"""


def build_dm_balance_prompt(board, game_state, skill_status):
    return f"""
你是 Blood on the Clocktower 的 DM（说书人）辅助平衡 Agent。

你的任务不是帮助玩家推理谁是坏人，而是帮助 DM 判断当前局势是否失衡，并给出主持层面的建议。

当前板子：
{json.dumps(board, ensure_ascii=False)}

当前游戏状态：
{json.dumps(game_state, ensure_ascii=False)}

当前技能可用状态：
{json.dumps(skill_status, ensure_ascii=False)}

严格要求：
1. 不要输出玩家推理结论
2. 不要直接说谁是坏人
3. 不要建议修改游戏基本规则
4. 不要建议 DM 凭空添加额外线索
5. 只能给出说书人可裁量范围内的平衡建议
6. 重点关注：信息位损失、保护位损失、摆烂状态、时间压缩、技能互动过强/过弱

输出 JSON，不要解释，不要 markdown。

输出格式：
{{
  "balance_assessment": "偏向善良阵营/偏向邪恶阵营/大致平衡",
  "risk_points": ["风险点1", "风险点2"],
  "dm_suggestions": ["建议1", "建议2"],
  "watch_list": ["关注点1", "关注点2"]
}}
"""