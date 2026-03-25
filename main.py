import json
from pathlib import Path

from core.board_rules import BOARD_RULES
from core.role_loader import load_roles, load_game_state
from core.board_builder import (
    filter_candidates,
    split_by_faction,
    compress_candidates,
    generate_board,
    recommend_bluffs,
)
from core.balance_checker import (
    validate_board,
    get_skill_availability,
    assist_dm_balance,
)
from core.llm_client import call_ollama, extract_json

ROLES_PATH = "data/roles.json"
GAME_STATE_PATH = "data/game_state.json"
BOARD_PATH = "data/generated_board.json"
BLUFF_PATH = "data/recommended_bluffs.json"
SKILL_STATUS_PATH = "data/skill_status.json"
DM_ADVICE_PATH = "data/dm_advice.json"

MAX_BOARD_RETRIES = 3


def save_json(path, data):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def ensure_file_exists(path, hint=""):
    if not Path(path).exists():
        raise FileNotFoundError(f"缺少文件: {path}\n{hint}")


def print_board_summary(script_name, num_players, theme, difficulty, board, issues, bluff_data):
    print("=" * 60)
    print(f"Script: {script_name}")
    print(f"Players: {num_players}")
    print(f"Theme: {theme}")
    print(f"Difficulty: {difficulty}")
    print("=" * 60)
    print("镇民:", "、".join(board.get("townsfolk", [])))
    print("外来者:", "、".join(board.get("outsiders", [])))
    print("爪牙:", "、".join(board.get("minions", [])))
    print("恶魔:", board.get("demon", ""))
    print()

    if board.get("reasoning"):
        print("配置说明:")
        print(board["reasoning"])
        print()

    if issues:
        print("规则检查发现问题:")
        for issue in issues:
            print("-", issue)
    else:
        print("规则检查通过。")

    print("\n推荐坏人伪装角色:")
    print("、".join(bluff_data.get("bluffs", [])))


def print_skill_status(skill_status):
    print("\n当前可发动技能的角色:")
    for item in skill_status["activatable"]:
        print(f"- {item['player']}（{item['role']}）: {item['reason']}")

    print("\n当前不可发动技能的角色:")
    for item in skill_status["blocked"]:
        print(f"- {item['player']}（{item['role']}）: {item['reason']}")

    print("\n当前被动/持续性角色:")
    for item in skill_status["passive"]:
        print(f"- {item['player']}（{item['role']}）: {item['reason']}")


def generate_valid_board(all_roles, num_players, theme, difficulty, rules):
    candidates = filter_candidates(all_roles, num_players)
    grouped_candidates = split_by_faction(candidates)
    compact_candidates = compress_candidates(grouped_candidates)

    last_board = None
    last_issues = None

    for attempt in range(1, MAX_BOARD_RETRIES + 1):
        board = generate_board(compact_candidates, num_players, rules, theme, difficulty)
        issues = validate_board(board, rules)

        if not issues:
            bluff_data = recommend_bluffs(board)
            return board, bluff_data, issues

        print(f"\n[第 {attempt} 次组板不合法，准备重试]")
        for issue in issues:
            print("-", issue)

        last_board = board
        last_issues = issues

    raise RuntimeError(
        f"连续 {MAX_BOARD_RETRIES} 次组板均不合法，请检查 prompt 或手动修正。\n"
        f"最后一次生成结果: {json.dumps(last_board, ensure_ascii=False, indent=2)}\n"
        f"问题: {last_issues}"
    )


def analyze_current_state(roles_data, all_roles, game_state):
    num_players = game_state["num_players"]
    theme = game_state.get("theme", "UNSW 校园悬疑")
    difficulty = game_state.get("difficulty", "中等")

    if num_players not in BOARD_RULES:
        raise ValueError(f"暂不支持 {num_players} 人局。")

    rules = BOARD_RULES[num_players]

    ensure_file_exists(
        BOARD_PATH,
        "请先把 game_state.json 里的 mode 设成 setup，运行一次生成初始板子。"
    )
    ensure_file_exists(
        BLUFF_PATH,
        "请先把 game_state.json 里的 mode 设成 setup，运行一次生成 bluff 推荐。"
    )

    board = load_json(BOARD_PATH)
    bluff_data = load_json(BLUFF_PATH)

    issues = validate_board(board, rules)
    if issues:
        raise RuntimeError(
            "当前 generated_board.json 不是合法板子，请重新 setup。\n"
            + "\n".join(f"- {issue}" for issue in issues)
        )

    print_board_summary(
        script_name=roles_data["script_name"],
        num_players=num_players,
        theme=theme,
        difficulty=difficulty,
        board=board,
        issues=issues,
        bluff_data=bluff_data,
    )

    skill_status = get_skill_availability(game_state, all_roles)
    print_skill_status(skill_status)

    dm_advice = assist_dm_balance(board, game_state, skill_status)
    print("\nDM 平衡辅助建议:")
    print(json.dumps(dm_advice, ensure_ascii=False, indent=2))

    save_json(SKILL_STATUS_PATH, skill_status)
    save_json(DM_ADVICE_PATH, dm_advice)

    print("\n已输出文件：")
    print("- data/skill_status.json")
    print("- data/dm_advice.json")


def setup_new_board(roles_data, all_roles, game_state):
    num_players = game_state["num_players"]
    theme = game_state.get("theme", "UNSW 校园悬疑")
    difficulty = game_state.get("difficulty", "中等")

    if num_players not in BOARD_RULES:
        raise ValueError(f"暂不支持 {num_players} 人局。")

    rules = BOARD_RULES[num_players]

    board, bluff_data, issues = generate_valid_board(
        all_roles=all_roles,
        num_players=num_players,
        theme=theme,
        difficulty=difficulty,
        rules=rules,
    )

    save_json(BOARD_PATH, board)
    save_json(BLUFF_PATH, bluff_data)

    print_board_summary(
        script_name=roles_data["script_name"],
        num_players=num_players,
        theme=theme,
        difficulty=difficulty,
        board=board,
        issues=issues,
        bluff_data=bluff_data,
    )

    print("\n已输出文件：")
    print("- data/generated_board.json")
    print("- data/recommended_bluffs.json")


def build_command_prompt(command, game_state):
    return f"""
你是一个 Blood on the Clocktower 游戏状态解析器。
你的任务是把 DM 的自然语言指令转换为对 game_state 的结构化修改。

当前 game_state：
{json.dumps(game_state, ensure_ascii=False)}

DM 指令：
{command}

要求：
1. 只输出 JSON，不要解释，不要 markdown
2. 只修改必要字段
3. 如果是增加/删除玩家状态，请直接给出更新后的完整列表
4. mode 只能是 setup 或 runtime
5. phase 只能是 day 或 night

输出格式：
{{
  "updates": {{
    "mode": "setup或runtime",
    "phase": "day或night",
    "night_number": 2,
    "day_number": 1,
    "alive_players": ["A","B"],
    "dead_players": ["H"],
    "drunk_players": ["A"],
    "silenced_players": [],
    "used_once_skills": ["Help Session"],
    "dm_notes": "..."
  }}
}}
"""


def apply_command_with_llm(command, game_state):
    prompt = build_command_prompt(command, game_state)
    raw = call_ollama(prompt)
    result = extract_json(raw)

    updates = result.get("updates", {})
    if not isinstance(updates, dict):
        raise ValueError("LLM 返回的 updates 不是合法对象。")

    new_state = dict(game_state)
    for key, value in updates.items():
        new_state[key] = value

    return new_state, updates


def interactive_loop(roles_data, all_roles, game_state):
    print("\n进入 DM 交互模式。")
    print("可用命令：show / setup / analyze / command / save / quit")
    print("说明：")
    print("- show：显示当前 game_state")
    print("- setup：根据当前 game_state 生成新板子")
    print("- analyze：基于当前板子 + 当前状态分析")
    print("- command：输入自然语言指令修改 game_state")
    print("- save：保存当前 game_state")
    print("- quit：退出")

    current_state = dict(game_state)

    while True:
        cmd = input("\n> ").strip().lower()

        if cmd == "quit":
            print("退出。")
            break

        elif cmd == "show":
            print(json.dumps(current_state, ensure_ascii=False, indent=2))

        elif cmd == "save":
            save_json(GAME_STATE_PATH, current_state)
            print("已保存到 data/game_state.json")

        elif cmd == "setup":
            current_state["mode"] = "setup"
            save_json(GAME_STATE_PATH, current_state)
            setup_new_board(roles_data, all_roles, current_state)

        elif cmd == "analyze":
            current_state["mode"] = "runtime"
            save_json(GAME_STATE_PATH, current_state)
            analyze_current_state(roles_data, all_roles, current_state)

        elif cmd == "command":
            user_command = input("请输入 DM 指令： ").strip()
            if not user_command:
                print("空指令，已跳过。")
                continue

            try:
                new_state, updates = apply_command_with_llm(user_command, current_state)
                current_state = new_state
                save_json(GAME_STATE_PATH, current_state)
                print("已更新 game_state.json")
                print("本次修改：")
                print(json.dumps(updates, ensure_ascii=False, indent=2))
            except Exception as e:
                print(f"指令解析失败：{e}")

        else:
            print("未知命令。可用：show / setup / analyze / command / save / quit")


def main():
    roles_data = load_roles(ROLES_PATH)
    all_roles = roles_data["roles"]
    game_state = load_game_state(GAME_STATE_PATH)

    mode = game_state.get("mode", "runtime")

    print(f"当前 mode: {mode}")

    if mode == "setup":
        setup_new_board(roles_data, all_roles, game_state)
    elif mode == "runtime":
        try:
            analyze_current_state(roles_data, all_roles, game_state)
        except FileNotFoundError as e:
            print(e)
            print("\n建议先运行 setup。")
    else:
        raise ValueError("game_state.json 中的 mode 只能是 setup 或 runtime")

    interactive_loop(roles_data, all_roles, game_state)


if __name__ == "__main__":
    main()