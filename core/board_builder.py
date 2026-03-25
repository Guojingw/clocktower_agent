from .llm_client import call_ollama, extract_json
from .prompts import build_board_prompt, build_bluff_prompt


def filter_candidates(roles, num_players):
    candidates = []
    for role in roles:
        if role["min_players"] <= num_players <= role["max_players"]:
            candidates.append(role)
    return candidates


def split_by_faction(candidates):
    grouped = {
        "townsfolk": [],
        "outsiders": [],
        "minions": [],
        "demon": []
    }
    faction_alias = {
        "minion": "minions",
        "outsider": "outsiders",
        "townsfolk": "townsfolk",
        "demon": "demon",
    }

    for role in candidates:
        faction = faction_alias.get(role["faction"], role["faction"])
        if faction not in grouped:
            raise KeyError(f"Unknown faction label: {role['faction']}")
        grouped[faction].append(role)

    return grouped


def compress_candidates(grouped_candidates):
    compressed = {}
    for faction, roles in grouped_candidates.items():
        compressed[faction] = [
            {
                "name": r["name"],
                "ability": r["ability"]
            }
            for r in roles
        ]
    return compressed


def generate_board(grouped_candidates, num_players, rules, theme, difficulty):
    prompt = build_board_prompt(grouped_candidates, num_players, rules, theme, difficulty)
    raw = call_ollama(prompt)
    return extract_json(raw)


def recommend_bluffs(board):
    prompt = build_bluff_prompt(board)
    raw = call_ollama(prompt)
    return extract_json(raw)