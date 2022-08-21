from typing import Dict, List
from wizwalker.combat import CombatMember
from src.combat_objects import id_to_member, school_to_str
from src.combat_utils import get_str_masteries, enemy_type_str, add_universal_stat, to_seperated_str_stats
import PySimpleGUI as gui

# UNFINISHED - slack

# STATS FORMAT
# NAME: example - SCHOOL: example
# POWER PIPS: X - PIPS: X
# SHADOW PIPS: X
# Boosts: Ice - 35%, Myth - 40%
# Resists: Fire - 70%, Storm - 80%
# Damages: Fire - 80%, Storm - 65%
# Criticals: Fire - 121, Storm - 272
# Blocks: Ice - 60, Myth - 50
# Masteries: Fire, Storm
# Max Possible Damage: 14000 (this won't come for a while)


async def total_stats_from_id(members: List[CombatMember], member_id: int) -> List:
    # Gets the readable relevant stats from
    member = await id_to_member(members, member_id)

    participant = await member.get_participant()
    stats = await member.get_stats()

    member_name = await member.name()
    member_type = await enemy_type_str(member)
    school_id = await participant.primary_magic_school_id()
    school_name = school_to_str[school_id]

    power_pips = await member.power_pips()
    pips = await member.normal_pips()
    shadow_pips = await member.shadow_pips()

    health = await member.health()
    max_health = await member.max_health()

    raw_resistances = await stats.dmg_reduce_percent()
    uni_resist = await stats.dmg_reduce_percent_all()
    real_resistances = add_universal_stat(raw_resistances, uni_resist)

    raw_damages = await stats.dmg_bonus_percent()
    uni_damage = await stats.dmg_bonus_percent_all()
    real_damages = add_universal_stat(raw_damages, uni_damage)

    raw_crits = await stats.critical_hit_rating_by_school()
    uni_crit = await stats.critical_hit_rating_all()
    real_crits = add_universal_stat(raw_crits, uni_crit)

    raw_blocks = await stats.block_rating_by_school()
    uni_block = await stats.block_rating_all()
    real_blocks = add_universal_stat(raw_blocks, uni_block)

    masteries = await get_str_masteries(member)
    masteries_str = ', '.join(masteries)

    resistances, raw_boosts = to_seperated_str_stats(real_resistances)

    damages, _ = to_seperated_str_stats(real_damages)
    crits, _ = to_seperated_str_stats(real_crits)
    blocks, _ = to_seperated_str_stats(real_blocks)

    total_stats = [
        f'Name: {member_name} - {member_type} - {school_name}',
        f'Power Pips: {power_pips} - Pips: {pips}',
        f'Shadow Pips: {shadow_pips}',
        f'Health: {health}/{max_health} ({(health / max_health) * 100}%)',
        f'Boosts: {dict_to_str(raw_boosts)}',
        f'Resists: {dict_to_str(resistances)}',
        f'Damages: {dict_to_str(damages)}',
        f'Crits: {dict_to_str(crits)}',
        f'Blocks: {dict_to_str(blocks)}',
        f'Masteries: {masteries_str}'
    ]

    return total_stats


def dict_to_str(input_dict: Dict[str, float], seperator_1: str = ': ', seperator_2: str = ', ') -> str:
    # Converts a str stats dict to a GUI readable list of stats
    output_str = ''
    for key in list(input_dict.keys()):
        output_str += f'{key}{seperator_1}{int(input_dict[key])}{seperator_2}'

    return output_str


def to_gui_str(stats, seperator: str = '\n') -> str:
    # Converts the total stats into GUI readable strings
    str_stats_list = []
    for stat in stats:
        if type(stat) == Dict[str, float]:
            str_stats_list.append(dict_to_str(stat))

        else:
            str_stats_list.append(str(stat))

    str_stats = seperator.join(str_stats_list)

    return str_stats