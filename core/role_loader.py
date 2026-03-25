import json


def load_roles(path="roles.json"):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_game_state(path="game_state.json"):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)