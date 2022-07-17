from typing import List
from wizwalker.combat import CombatMember
from wizwalker.memory.memory_objects.spell_effect import DynamicSpellEffect
from wizwalker.memory.memory_objects.game_stats import DynamicGameStats


school_ids = {0: 2343174, 1: 72777, 2: 83375795, 3: 2448141, 4: 2330892, 5: 78318724, 6: 1027491821, 7: 2625203, 8: 78483, 9: 2504141, 10: 663550619, 11: 1429009101, 12: 1488274711, 13: 1760873841, 14: 806477568, 15: 931528087}
school_list_ids = {index: i for i, index in school_ids.items()}
school_id_list = list(school_ids.values())

side_excluded_ids = [663550619, 806477568, 931528087, 1488274711, 1760873841]
shadow_excluded_ids = [1429009101]
astral_excluded_ids = [78483, 2625203, 2504141]

non_main_excluded_ids = side_excluded_ids + shadow_excluded_ids + astral_excluded_ids



class InvalidSchoolID(Exception):
	'''Raised when a school ID is not valid'''
	pass



def get_school_stat(stats: List, school_id: int):
	# Returns the specific element in a list corresponding to a school ID
	if school_id in school_id_list:
		stat_index = school_list_ids[school_id]
		return stats[stat_index]
	else:
		raise InvalidSchoolID


def get_relevant_school_stats(stats: List, excluded_ids: List[int]):
	# Inputs any list of stats and outputs a list excluding those in a list of excluded school IDs
	relevant_stats = []
	for i, stat in enumerate(stats):
		if school_ids[i] not in excluded_ids:
			relevant_stats.append(stat)

	return relevant_stats


async def get_game_stats(member: CombatMember) -> DynamicGameStats:
	# Returns the GameStats from a CombatMember
	participant = await member.get_participant()
	game_stats = await participant.game_stats()
	return game_stats


async def get_hanging_effects(member: CombatMember) -> List[DynamicSpellEffect]:
	# Returns the Hanging Effects from a CombatMember
	participant = await member.get_participant()
	hanging_effects = await participant.hanging_effects()
	return hanging_effects


async def get_aura_effects(member: CombatMember) -> List[DynamicSpellEffect]:
	# Returns the Aura Effects from a CombatMember
	participant = await member.get_participant()
	aura_effects = await participant.aura_effects()
	return aura_effects


async def get_shadow_effects(member: CombatMember) -> List[DynamicSpellEffect]:
	# Returns the Shadow Form Effects from a CombatMember
	participant = await member.get_participant()
	shadow_effects = await participant.shadow_spell_effects()
	return shadow_effects