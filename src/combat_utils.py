from typing import Any, Coroutine, List, Dict, Tuple
from wizwalker.combat import CombatMember
from wizwalker.memory.memory_objects.combat_participant import DynamicGameStats
from wizwalker.memory.memory_objects.spell_effect import SpellEffects
from src.combat_objects import school_ids, school_names
from src.utils import index_with_str
import re
# UNFINISHED - slack


symbol_to_effect_type = {
    'Afterlife': SpellEffects.afterlife,
    'DamageOverTime': SpellEffects.damage_over_time,
    'HealOverTime': SpellEffects.heal_over_time,
    'DeferredDamage': SpellEffects.deferred_damage,
    'Jinx': SpellEffects.modify_incoming_damage,
    'Trap': SpellEffects.modify_incoming_damage,
    'Ward': SpellEffects.modify_incoming_damage,
    'Resist': SpellEffects.modify_incoming_damage,
    'Curse': SpellEffects.modify_outgoing_damage,
    'Blade': SpellEffects.modify_outgoing_damage
}



def generate_mastery_funcs(stats: DynamicGameStats) -> List[Coroutine[Any, Any, int]]:
    mastery_funcs = [stats.fire_mastery, stats.ice_mastery, stats.storm_mastery, stats.myth_mastery, stats.life_mastery, stats.death_mastery, stats.balance_mastery]
    return mastery_funcs


def add_universal_stat(input_stats: List[float], uni_stat: float) -> List[float]:
    # Adds a universal stat to every school-specific stat.
    real_stats = []
    for stat in input_stats:
        real_stat = stat + uni_stat
        real_stats.append(real_stat)

    return real_stats


def to_percent_str(input_stats: List[float]) -> List[str]:
    # Converts a list of stats into readable percentage values for use in the GUI
    readable_stats = []
    for stat in input_stats:
        readable_stats.append(str(f'{stat * 100}%'))

    return readable_stats


def to_percent(input_stats: List[float]) -> List[float]:
    # Converts a list of stats into readable percentage values for use in the GUI
    readable_stats = []
    for stat in input_stats:
        readable_stats.append(stat * 100)

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
        if stat > 0.0:
            positives[index_name] = stat

        elif stat < 0.0:
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


def content_from_str(input_str: str, seperator: str = '') -> str:
    # Returns the relevant text content from a string read from a window
    return seperator.join(re.findall('>.*?<', input_str))


def image_name_from_str(input_str: str) -> str:
    # Returns the name of the first image in a string read from a window, without the path
    start_index = index_with_str(input_str, ';') + 1
    end_index = index_with_str(input_str[start_index:], ';')

    image_path = input_str[start_index:end_index]

    slash_index = index_with_str(image_path, '/') + 1
    filetype_index = index_with_str(image_path, '.')

    return image_path[slash_index:filetype_index]


def total_effects_from_str(input_str: str) -> List[Tuple[SpellEffects, float, int, int, str, SpellEffects, int, str]]:
    # OUTPUT OBJECT: List of (SpellEffect type, effect param, effect school, effect amount, Conditional SpellEffect type, )
    if 'Clear' in input_str:
        start_index = index_with_str(input_str, '(')
        end_index = index_with_str(input_str, ')')

        if end_index == len(input_str) - 1:
            end_index = None

        condition_amount = int(input_str[start_index:end_index])
