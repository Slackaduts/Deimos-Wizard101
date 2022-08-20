from typing import Any, Coroutine, List, Dict, Tuple
from wizwalker.combat import CombatMember
from wizwalker.memory.memory_objects.combat_participant import DynamicGameStats
from src.combat_objects import school_ids, school_names
# UNFINISHED - slack

def generate_mastery_funcs(stats: DynamicGameStats) -> List[Coroutine[Any, Any, int]]:
    mastery_funcs = [stats.fire_mastery, stats.ice_mastery, stats.storm_mastery, stats.myth_mastery, stats.life_mastery, stats.death_mastery, stats.balance_mastery]
    return mastery_funcs


def add_universal_stat(input_stats: List[float], uni_stat: float) -> List[float]:
    # Adds a universal stat to every school-specific stat.
    real_stats = []
    for stat in input_stats:
        real_stats.append(stat + uni_stat)

    return real_stats


def to_percent_str(input_stats: List[float]) -> List[str]:
    # Converts a list of stats into readable percentage values for use in the GUI
    readable_stats = []
    for stat in input_stats:
        readable_stats.append(str(f'{stat * 100}%'))

    return readable_stats


def to_relevant_stats(input_stats: List[float], blacklist: List[str] = [10, 12, 13, 14, 15]) -> Dict[int, float]:
    # Gets rid of the irrelevant stats (Cantrips, Gardening, etc) from a stats list. Outputs a dict with the ID of each school as the key.
    output_stats: Dict[int, float] = {}

    for i, stat in enumerate(input_stats):
        if i not in blacklist:
            index_id = school_ids[i]
            output_stats[index_id] = stat


def to_relevant_str_stats(input_stats: List[float], blacklist: List[str] = [10, 12, 13, 14, 15]) -> Dict[str, float]:
    # Gets rid of the irrelevant stats (Cantrips, Gardening, etc) from a stats list. Outputs a dict with the ID of each school as the key.
    output_stats: Dict[int, float] = {}

    for i, stat in enumerate(input_stats):
        if i not in blacklist:
            index_name = school_names[i]
            output_stats[index_name] = stat


def to_seperated_str_stats(input_stats: List[float]) -> Tuple[Dict[str, float], Dict[str, float]]:
    # Seperates a list of stats into 2 dicts, positives and negatives, string name correlating to each stat
    positives: Dict[str, float] = {}
    negatives: Dict[str, float] = {}

    for i, stat in enumerate(input_stats):
        index_name = school_names[i]
        if stat > 0:
            positives[index_name] = stat

        elif stat < 0:
            negatives[index_name] = stat

    return (positives, negatives)


async def get_str_masteries(member: CombatMember) -> List[str]:
    # Returns a list of the masteries a CombatMember has, by name
    stats = await member.get_stats()

    mastery_funcs = generate_mastery_funcs(stats)
    mastery_str = ['Fire', 'Ice', 'Storm', 'Myth', 'Life', 'Death', 'Balance']
    masteries = []

    for mastery, str in zip(mastery_funcs, mastery_str):
        if await mastery():
            masteries.append(str)

    return masteries


async def get_masteries(member: CombatMember) -> List[int]:
    # Returns a list of the masteries a CombatMember has, by school ID
    stats = await member.get_stats()

    mastery_funcs = generate_mastery_funcs(stats)
    masteries = [mastery for mastery in mastery_funcs]

    return masteries


async def enemy_type_str(member: CombatMember) -> str:
    if await member.is_boss():
        return 'Boss'

    elif await member.is_minion():
        return "Minion"

    elif await member.is_monster():
        return "Mob"

    else:
        return "Player"