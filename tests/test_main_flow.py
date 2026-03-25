import io
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import main


TEST_ROLES = {
    "script_name": "UNSW: No one Fail",
    "roles": [
        {"name": "选课助手", "faction": "townsfolk", "ability": "每晚选择一名玩家。", "min_players": 7, "max_players": 12},
        {"name": "Moodle爬虫", "faction": "townsfolk", "ability": "每晚得知昨晚全场摆烂人数。", "min_players": 7, "max_players": 12},
        {"name": "Help Session", "faction": "townsfolk", "ability": "一次性保护。", "min_players": 7, "max_players": 12},
        {"name": "情绪感染者", "faction": "townsfolk", "ability": "一次性让一人摆烂。", "min_players": 7, "max_players": 12},
        {"name": "咖啡狂人", "faction": "townsfolk", "ability": "持续影响邻座。", "min_players": 7, "max_players": 12},
        {"name": "社恐分子", "faction": "outsider", "ability": "每晚问一个是/否问题。", "min_players": 7, "max_players": 12},
        {"name": "火警空响", "faction": "minion", "ability": "每晚选择一个玩家，使其白天审判失败。", "min_players": 7, "max_players": 12},
        {"name": "Final吞噬者", "faction": "demon", "ability": "非首夜可发动特殊效果。", "min_players": 7, "max_players": 12}
    ]
}

TEST_GAME_STATE_SETUP = {
    "mode": "setup",
    "num_players": 8,
    "theme": "UNSW 校园悬疑",
    "difficulty": "中等",
    "phase": "night",
    "night_number": 2,
    "day_number": 1,
    "alive_players": ["A", "B", "C", "D", "E", "F", "G"],
    "dead_players": ["H"],
    "player_roles": {
        "A": "选课助手",
        "B": "Moodle爬虫",
        "C": "火警空响",
        "D": "Final吞噬者",
        "E": "社恐分子",
        "F": "Help Session",
        "G": "情绪感染者",
        "H": "咖啡狂人"
    },
    "drunk_players": ["A"],
    "used_once_skills": ["Help Session"],
    "silenced_players": [],
    "nominated_today": ["A", "F"],
    "revealed_or_confirmed_roles": {
        "H": "咖啡狂人"
    },
    "day_phase_notes": [
        "白天讨论时间曾被压缩一次",
        "当前公开信息较少"
    ],
    "dm_notes": "目前好人推理困难，坏人尚未明显暴露；保护位已损失一人。"
}


class TestClocktowerAgentFlow(unittest.TestCase):
    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())

        data_dir = self.tmpdir / "data"
        data_dir.mkdir(parents=True, exist_ok=True)

        (data_dir / "roles.json").write_text(
            json.dumps(TEST_ROLES, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        (data_dir / "game_state.json").write_text(
            json.dumps(TEST_GAME_STATE_SETUP, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

        self.roles_path = str(data_dir / "roles.json")
        self.game_state_path = str(data_dir / "game_state.json")
        self.board_path = str(data_dir / "generated_board.json")
        self.bluff_path = str(data_dir / "recommended_bluffs.json")
        self.skill_status_path = str(data_dir / "skill_status.json")
        self.dm_advice_path = str(data_dir / "dm_advice.json")

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def _fake_generate_board(self, *args, **kwargs):
        return {
            "townsfolk": ["选课助手", "Moodle爬虫", "Help Session", "情绪感染者", "咖啡狂人"],
            "outsiders": ["社恐分子"],
            "minions": ["火警空响"],
            "demon": "Final吞噬者",
            "reasoning": "测试用合法板子。"
        }

    def _fake_recommend_bluffs(self, *args, **kwargs):
        return {
            "bluffs": ["情绪感染者", "咖啡狂人", "Help Session"]
        }

    def _fake_assist_dm_balance(self, *args, **kwargs):
        return {
            "balance_assessment": "偏向邪恶阵营",
            "risk_points": ["好人信息偏少"],
            "dm_suggestions": ["注意信息位损失"],
            "watch_list": ["A（选课助手）", "D（Final吞噬者）"]
        }

    @patch("main.interactive_loop")
    @patch("main.assist_dm_balance")
    @patch("main.recommend_bluffs")
    @patch("main.generate_board")
    def test_setup_mode_generates_board_files(
        self,
        mock_generate_board,
        mock_recommend_bluffs,
        mock_assist_dm_balance,
        mock_interactive_loop
    ):
        mock_generate_board.side_effect = self._fake_generate_board
        mock_recommend_bluffs.side_effect = self._fake_recommend_bluffs
        mock_assist_dm_balance.side_effect = self._fake_assist_dm_balance

        with patch.object(main, "ROLES_PATH", self.roles_path), \
             patch.object(main, "GAME_STATE_PATH", self.game_state_path), \
             patch.object(main, "BOARD_PATH", self.board_path), \
             patch.object(main, "BLUFF_PATH", self.bluff_path), \
             patch.object(main, "SKILL_STATUS_PATH", self.skill_status_path), \
             patch.object(main, "DM_ADVICE_PATH", self.dm_advice_path):

            main.main()

        self.assertTrue(Path(self.board_path).exists())
        self.assertTrue(Path(self.bluff_path).exists())

        board = json.loads(Path(self.board_path).read_text(encoding="utf-8"))
        self.assertEqual(len(board["townsfolk"]), 5)
        self.assertEqual(len(board["outsiders"]), 1)
        self.assertEqual(len(board["minions"]), 1)
        self.assertEqual(board["demon"], "Final吞噬者")

    @patch("main.interactive_loop")
    @patch("main.assist_dm_balance")
    def test_runtime_mode_generates_skill_status_and_dm_advice(
        self,
        mock_assist_dm_balance,
        mock_interactive_loop
    ):
        # 先手动准备合法板子和 bluff
        Path(self.board_path).write_text(
            json.dumps({
                "townsfolk": ["选课助手", "Moodle爬虫", "Help Session", "情绪感染者", "咖啡狂人"],
                "outsiders": ["社恐分子"],
                "minions": ["火警空响"],
                "demon": "Final吞噬者",
                "reasoning": "测试用合法板子。"
            }, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

        Path(self.bluff_path).write_text(
            json.dumps({
                "bluffs": ["情绪感染者", "咖啡狂人", "Help Session"]
            }, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

        runtime_state = dict(TEST_GAME_STATE_SETUP)
        runtime_state["mode"] = "runtime"
        Path(self.game_state_path).write_text(
            json.dumps(runtime_state, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

        mock_assist_dm_balance.side_effect = self._fake_assist_dm_balance

        with patch.object(main, "ROLES_PATH", self.roles_path), \
             patch.object(main, "GAME_STATE_PATH", self.game_state_path), \
             patch.object(main, "BOARD_PATH", self.board_path), \
             patch.object(main, "BLUFF_PATH", self.bluff_path), \
             patch.object(main, "SKILL_STATUS_PATH", self.skill_status_path), \
             patch.object(main, "DM_ADVICE_PATH", self.dm_advice_path):

            main.main()

        self.assertTrue(Path(self.skill_status_path).exists())
        self.assertTrue(Path(self.dm_advice_path).exists())

        skill_status = json.loads(Path(self.skill_status_path).read_text(encoding="utf-8"))
        dm_advice = json.loads(Path(self.dm_advice_path).read_text(encoding="utf-8"))

        self.assertIn("activatable", skill_status)
        self.assertIn("blocked", skill_status)
        self.assertEqual(dm_advice["balance_assessment"], "偏向邪恶阵营")

    def test_validate_board_rule_count(self):
        from core.balance_checker import validate_board
        from core.board_rules import BOARD_RULES

        valid_board = {
            "townsfolk": ["选课助手", "Moodle爬虫", "Help Session", "情绪感染者", "咖啡狂人"],
            "outsiders": ["社恐分子"],
            "minions": ["火警空响"],
            "demon": "Final吞噬者"
        }

        issues = validate_board(valid_board, BOARD_RULES[8])
        self.assertEqual(issues, [])

    def test_get_skill_availability_basic(self):
        from core.balance_checker import get_skill_availability

        state = dict(TEST_GAME_STATE_SETUP)
        result = get_skill_availability(state, TEST_ROLES["roles"])

        activatable_roles = {x["role"] for x in result["activatable"]}
        blocked_roles = {x["role"] for x in result["blocked"]}

        self.assertIn("Moodle爬虫", activatable_roles)
        self.assertIn("火警空响", activatable_roles)
        self.assertIn("Final吞噬者", activatable_roles)
        self.assertIn("选课助手", blocked_roles)  # A 摆烂
        self.assertIn("Help Session", blocked_roles)  # 已使用一次性技能


if __name__ == "__main__":
    unittest.main()