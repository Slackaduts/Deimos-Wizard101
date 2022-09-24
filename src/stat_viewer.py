import asyncio
from typing import Dict, List, Tuple
from wizwalker import Client
from wizwalker.errors import MemoryInvalidated
from wizwalker.combat import CombatHandler
from src.combat_objects import school_to_str
from src.combat_utils import get_str_masteries, enemy_type_str, add_universal_stat, to_seperated_str_stats, to_percent
from src.combat_math import base_damage_calculation_from_id

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

damage_per_pip = {
	2343174: 100,
	72777: 83,
	83375795: 125,
	78318724: 85,
	2330892: 83,
	2448141: 90,
	1027491821: 85
}

shadow_damage_per_pip = {
	2343174: 120,
	72777: 100,
	83375795: 130,
	78318724: 105,
	2330892: 100,
	2448141: 115,
	1027491821: 105
}


async def total_stats(client: Client, caster_index: int, target_index: int, base_damage: int = None, school_id: int = None, force_crit: bool = None, force_school: bool = False) -> Tuple[List[str], List[str], int, int]:
    # Gets the readable relevant stats from
    combat = CombatHandler(client)
    try:
        members = await combat.get_members()
        if len(members) < caster_index:
            caster_index = len(members) - 1

        else:
            caster_index -= 1

        if len(members) < target_index:
            target_index = len(members) - 1

        else:
            target_index -= 1

        member = members[caster_index]
        target = members[target_index]

        member_id = await member.owner_id()
        target_id = await target.owner_id()
        participant = await member.get_participant()
        stats = await member.get_stats()

    except MemoryInvalidated:
        await asyncio.sleep(0.5)
        await total_stats(client, caster_index, target_index, base_damage)

    else:
        member_names = [await m.name() for m in members]
        names_with_indexes = [f'{i + 1} - {name}' for i, name in enumerate(member_names)]
        member_name = await member.name()
        member_type = await enemy_type_str(member)
        if not school_id or not force_school:
            school_id = await participant.primary_magic_school_id()

        real_school_id = await participant.primary_magic_school_id()

        school_name = school_to_str[real_school_id]
        temp_school_name = school_to_str[school_id]

        power_pips = await member.power_pips()
        pips = await member.normal_pips()
        shadow_pips = await member.shadow_pips()

        health = await member.health()
        max_health = await member.max_health()

        raw_resistances = await stats.dmg_reduce_percent()
        uni_resist = await stats.dmg_reduce_percent_all()
        real_resistances = to_percent(add_universal_stat(raw_resistances, uni_resist))

        raw_damages = await stats.dmg_bonus_percent()
        uni_damage = await stats.dmg_bonus_percent_all()
        real_damages = to_percent(add_universal_stat(raw_damages, uni_damage))

        raw_pierces = await stats.ap_bonus_percent()
        uni_pierce = await stats.ap_bonus_percent_all()
        real_pierces = to_percent(add_universal_stat(raw_pierces, uni_pierce))

        raw_crits = await stats.critical_hit_rating_by_school()
        uni_crit = await stats.critical_hit_rating_all()
        real_crits = add_universal_stat(raw_crits, uni_crit)

        raw_blocks = await stats.block_rating_by_school()
        uni_block = await stats.block_rating_all()
        real_blocks = add_universal_stat(raw_blocks, uni_block)

        masteries = await get_str_masteries(member)
        masteries_str = ', '.join(masteries)

        total_pips = (power_pips * 2) + (shadow_pips * 3.6) + pips

        if school_id in damage_per_pip:
            dpp = shadow_damage_per_pip[school_id]

        else:
            dpp = 100

        if not base_damage:
            base_damage = dpp * total_pips

        global_effect = None
        combat_resolver = await client.duel.combat_resolver()
        if combat_resolver:
            global_effect = await combat_resolver.global_effect()

        estimated_damage = await base_damage_calculation_from_id(client, members, member_id, target_id, base_damage, school_id, global_effect, force_crit=force_crit)

        resistances, raw_boosts = to_seperated_str_stats(real_resistances)

        damages, _ = to_seperated_str_stats(real_damages)
        pierces, _ = to_seperated_str_stats(real_pierces)
        crits, _ = to_seperated_str_stats(real_crits)
        blocks, _ = to_seperated_str_stats(real_blocks)

        if await member.is_player() and await target.is_player():
            total_stats = ['The stat viewer is not supported in PvP.']

        else:
            total_stats = [
                f'Estimated Max Dmg Against {await target.name()}: {int(estimated_damage)}',
                f'Name: {member_name} - {member_type} - {school_name}',
                f'Power Pips: {power_pips} - Pips: {pips}',
                f'Shadow Pips: {shadow_pips}',
                f'Health: {health}/{max_health} ({(health // max_health) * 100}%)',
                f'Boosts: {dict_to_str(raw_boosts, take_abs=True)}',
                f'Resists: {dict_to_str(resistances)}',
                f'Damages: {dict_to_str(damages)}',
                f'Pierces: {dict_to_str(pierces)}',
                f'Crits: {dict_to_str(crits)}',
                f'Blocks: {dict_to_str(blocks)}',
                f'Masteries: {masteries_str}',
            ]

        return (total_stats, names_with_indexes, caster_index, target_index, temp_school_name)


def dict_to_str(input_dict: Dict[str, float], seperator_1: str = ': ', seperator_2: str = ', ', take_abs: bool = False, key_blacklist: List[str] = ['WhirlyBurly', 'Gardening', 'CastleMagic', 'Cantrips', 'Fishing']) -> str:
    # Converts a str stats dict to a GUI readable list of stats
    output_str = ''
    for key in list(input_dict.keys()):
        if key not in key_blacklist:
            if not take_abs:
                output_str += f'{key}{seperator_1}{int(input_dict[key])}{seperator_2}'

            else:
                output_str += f'{key}{seperator_1}{abs(int(input_dict[key]))}{seperator_2}'

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