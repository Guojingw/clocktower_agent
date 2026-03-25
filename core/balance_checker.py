from core.llm_client import call_ollama, extract_json
from core.prompts import build_dm_balance_prompt

ONCE_ONLY_ROLES = {
    "Help Session",
    "老师罢工",
    "情绪感染者",
    "组会代言人",
    "背刺者",
    "挂科乌龙",
}

PASSIVE_OR_ALWAYS_ON_ROLES = {
    "Special Consideration",
    "必过锦鲤",
    "内卷之王",
    "咖啡狂人",
}

DAY_ACTIVE_ROLES = {
    "组会爆发者",
    "组会代言人",
}


def validate_board(board, rules):
    issues = []

    def count_or_zero(key):
        if key == "demon":
            return 1 if board.get("demon") else 0
        return len(board.get(key, []))

    for faction, expected in rules.items():
        actual = count_or_zero(faction)
        if actual != expected:
            issues.append(f"{faction} 数量应为 {expected}，实际为 {actual}")

    all_roles = []
    for faction in ["townsfolk", "outsiders", "minions"]:
        all_roles.extend(board.get(faction, []))
    if board.get("demon"):
        all_roles.append(board["demon"])

    if len(all_roles) != len(set(all_roles)):
        issues.append("存在重复角色")

    return issues


def infer_activation_type(role_name: str):
    first_night_roles = {
        "群聊视奸者",
        "早八抢课人"
    }

    each_night_roles = {
        "Lecture回放",
        "抄袭雷达",
        "选课助手",
        "Moodle爬虫",
        "社恐分子",
        "火警空响",
        "学术警告",
        "组会鸽王",
        "Hurdle幽灵",
        "三学期暴君",
        "Deadline降临者"
    }

    other_night_roles = {
        "Final吞噬者"
    }

    once_roles = ONCE_ONLY_ROLES
    passive_roles = PASSIVE_OR_ALWAYS_ON_ROLES
    day_active_roles = DAY_ACTIVE_ROLES

    if role_name in first_night_roles:
        return "first_night"
    if role_name in each_night_roles:
        return "each_night"
    if role_name in other_night_roles:
        return "other_night"
    if role_name in once_roles:
        return "once"
    if role_name in passive_roles:
        return "passive"
    if role_name in day_active_roles:
        return "day_active"
    return "unknown"


def get_skill_availability(game_state, roles):
    phase = game_state.get("phase", "night")
    night_number = game_state.get("night_number", 1)
    alive_players = set(game_state.get("alive_players", []))
    drunk_players = set(game_state.get("drunk_players", []))
    used_once_skills = set(game_state.get("used_once_skills", []))
    player_roles = game_state.get("player_roles", {})

    activatable = []
    blocked = []
    passive = []

    for player, role_name in player_roles.items():
        activation_type = infer_activation_type(role_name)

        if player not in alive_players:
            blocked.append({
                "player": player,
                "role": role_name,
                "reason": "玩家已死亡"
            })
            continue

        if activation_type == "passive":
            passive.append({
                "player": player,
                "role": role_name,
                "reason": "被动技能"
            })
            continue

        if player in drunk_players:
            blocked.append({
                "player": player,
                "role": role_name,
                "reason": "玩家处于摆烂状态"
            })
            continue

        if activation_type == "once" and role_name in used_once_skills:
            blocked.append({
                "player": player,
                "role": role_name,
                "reason": "一次性技能已使用"
            })
            continue

        if phase == "night":
            if activation_type == "first_night" and night_number != 1:
                blocked.append({
                    "player": player,
                    "role": role_name,
                    "reason": "该技能仅首夜可发动"
                })
                continue

            if activation_type == "other_night" and night_number == 1:
                blocked.append({
                    "player": player,
                    "role": role_name,
                    "reason": "该技能非首夜发动"
                })
                continue

            if activation_type in {"each_night", "first_night", "other_night", "once"}:
                activatable.append({
                    "player": player,
                    "role": role_name,
                    "reason": "当前夜晚可发动"
                })
                continue

            blocked.append({
                "player": player,
                "role": role_name,
                "reason": "不是夜晚发动技能"
            })
            continue

        if phase == "day":
            if activation_type == "day_active":
                activatable.append({
                    "player": player,
                    "role": role_name,
                    "reason": "当前白天可发动"
                })
                continue

            blocked.append({
                "player": player,
                "role": role_name,
                "reason": "不是白天发动技能"
            })
            continue

    return {
        "activatable": activatable,
        "blocked": blocked,
        "passive": passive
    }


def assist_dm_balance(board, game_state, skill_status):
    prompt = build_dm_balance_prompt(board, game_state, skill_status)
    raw = call_ollama(prompt)
    return extract_json(raw)