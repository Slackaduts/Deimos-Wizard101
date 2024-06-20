from __future__ import annotations
from pathlib import Path
from loguru import logger


import yaml


# QuestBot is split into two parts so we don't have to keep all the code in memory at all times
class QuestBotInfo:
    def __init__(self, author: str, quest_name: str, goal_name: str, path: Path):
        author = author
        self.quest_name = quest_name
        self.goal_name = goal_name
        self.path = path

    def load_bot(self) -> QuestBot:
        return QuestBot(self)

class QuestBot:
    def __init__(self, info: QuestBotInfo):
        self.info = info
        with open(info.path, "r") as f:
            self._raw = yaml.load(f, Loader=yaml.SafeLoader)
        assert self.info.quest_name == self._raw["quest"]
        assert self.info.goal_name == self._raw["goal"]

    def get_code(self) -> str:
        return self._raw["code"]


class QuestBotManager:
    def __init__(self, bots_path: Path):
        self._bots_path = bots_path
        # TODO: Load a bot index instead of fetching every single file. Should only load ones not in index and put them into the index.

        self._bot_table: dict[str, list[QuestBotInfo]] = {}
        for path in self._bots_path.iterdir():
            if not path.is_file():
                continue
            with open(path, "r") as f:
                raw = yaml.load(f, Loader=yaml.SafeLoader)
            author = raw["author"]
            quest_name = raw["quest"].lower()
            quest_goal = raw["goal"].lower()

            goal_list = self._bot_table.setdefault(quest_name, [])
            if quest_goal in goal_list:
                raise RuntimeError(f"Tried loading multiple bots for quest `{quest_name}` - {quest_goal}")
            goal_list.append(QuestBotInfo(
                author=author,
                quest_name=quest_name,
                goal_name=quest_goal,
                path=path,
            ))
            logger.info(f'Loaded bot: "{quest_name}" - "{quest_goal}"')

    def has_bot_for(self, quest_name: str, quest_goal: str) -> bool:
        if not quest_name in self._bot_table:
            return False
        for goal in self._bot_table[quest_name]:
            if quest_goal.startswith(goal.goal_name):
                return True
        return False

    def fetch_bot_info(self, quest_name: str, quest_goal: str) -> QuestBotInfo:
        assert self.has_bot_for(quest_name, quest_goal)
        for goal in self._bot_table[quest_name]:
            if quest_goal.startswith(goal.goal_name):
                return goal
        assert False, "Unreachable"
