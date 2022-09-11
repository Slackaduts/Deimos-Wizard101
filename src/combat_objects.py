from typing import List
from wizwalker.combat import CombatMember, CombatCard
from wizwalker.memory.memory_objects.spell_effect import DynamicSpellEffect
from wizwalker.memory.memory_objects.game_stats import DynamicGameStats


school_ids = {0: 2343174, 1: 72777, 2: 83375795, 3: 2448141, 4: 2330892, 5: 78318724, 6: 1027491821, 7: 2625203, 8: 78483, 9: 2504141, 10: 663550619, 11: 1429009101, 12: 1488274711, 13: 1760873841, 14: 806477568, 15: 931528087}
school_id_to_names = {'Fire': 2343174, 'Ice': 72777, 'Storm': 83375795, 'Myth': 2448141, 'Life': 2330892, 'Death': 78318724, 'Balance': 1027491821, 'Star': 2625203, 'Sun': 78483, 'Moon': 2504141, 'Gardening': 663550619, 'Shadow': 1429009101, 'Fishing': 1488274711, 'Cantrips': 1760873841, 'CastleMagic': 806477568, 'WhirlyBurly': 931528087}
school_to_str = {index: i for i, index in school_id_to_names.items()}
school_list_ids = {index: i for i, index in school_ids.items()}
school_names = list(school_id_to_names.keys())
school_id_list = list(school_ids.values())

side_excluded_ids = [663550619, 806477568, 931528087, 1488274711, 1760873841]
shadow_excluded_ids = [1429009101]
astral_excluded_ids = [78483, 2625203, 2504141]

non_main_excluded_ids = side_excluded_ids + shadow_excluded_ids + astral_excluded_ids

opposite_school_ids = {72777: 2343174, 2330892: 78318724, 2343174: 72777, 2448141: 83375795, 78318724: 2330892, 83375795: 2448141}



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


async def get_game_stats(member_id: int, members: List[CombatMember]) -> DynamicGameStats:
	# Returns the GameStats from a CombatMember
	member = await id_to_member(member_id, members)
	participant = await member.get_participant()
	game_stats = await participant.game_stats()
	return game_stats


async def get_hanging_effects(member_id: int, members: List[CombatMember]) -> List[DynamicSpellEffect]:
	# Returns the Hanging Effects from a CombatMember
	member = await id_to_member(member_id, members)
	participant = await member.get_participant()
	hanging_effects = await participant.hanging_effects()
	return hanging_effects


async def get_aura_effects(member_id: int, members: List[CombatMember]) -> List[DynamicSpellEffect]:
	# Returns the Aura Effects from a CombatMember
	member = await id_to_member(member_id, members)
	participant = await member.get_participant()
	aura_effects = await participant.aura_effects()
	return aura_effects


async def get_shadow_effects(member_id: int, members: List[CombatMember]) -> List[DynamicSpellEffect]:
	# Returns the Shadow Form Effects from a CombatMember
	member = await id_to_member(member_id, members)
	participant = await member.get_participant()
	shadow_effects = await participant.shadow_spell_effects()
	return shadow_effects


async def get_total_effects(member_id: int, members: List[CombatMember]) -> List[DynamicSpellEffect]:
	# Gets all the hanging effects from a CombatMember
	effects: List[DynamicSpellEffect] = []
	effects += await get_hanging_effects(member_id, members)
	effects += await get_aura_effects(member_id, members)
	effects += await get_shadow_effects(member_id, members)
	return effects


async def ids_from_cards(cards: List[CombatCard]) -> List[int]:
	# Returns a list of spell IDs from a list of cards, 1:1
	spell_ids: List[int] = []
	for card in cards:
		spell_id = await card.spell_id()
		spell_ids.append(spell_id)

	return spell_ids


async def id_to_member(member_id: int, members: List[CombatMember]) -> CombatMember:
	# Returns a CombatMember with a given ID
	for member in members:
		if await member.owner_id() == member_id:
			return member

	raise ValueError


async def id_to_card(spell_id: int, cards: List[CombatCard]) -> CombatCard:
	for card in cards:
		if await card.spell_id() == spell_id:
			return card

	raise ValueError


async def id_to_hanging_effects(member_id: int, members: List[CombatMember]) -> List[DynamicSpellEffect]:
	# Returns the hanging effects from a given CombatMember ID
	member = await id_to_member(members, member_id)

	effects = await get_hanging_effects(member)

	return effects


async def id_to_aura_effects(member_id: int, members: List[CombatMember]) -> List[DynamicSpellEffect]:
	# Returns the aura effects from a given CombatMember ID
	member = await id_to_member(members, member_id)

	effects = await get_aura_effects(member)

	return effects


async def id_to_shadow_effects(member_id: int, members: List[CombatMember]) -> List[DynamicSpellEffect]:
	# Returns the shadow effects from a given CombatMember ID
	member = await id_to_member(members, member_id)

	effects = await get_shadow_effects(member)

	return effects


async def id_to_total_effects(member_id: int, members: List[CombatMember]) -> List[DynamicSpellEffect]:
	# Returns the total effects from a given CombatMember ID
	member = await id_to_member(members, member_id)

	effects = await get_total_effects(member)

	return effects


async def spell_id_to_effects(spell_id: int, cards: List[CombatCard]) -> List[DynamicSpellEffect]:
	# Returns the spell effects for a card corresponding to a spell ID.

	card = await id_to_card(cards, spell_id)

	if card:
		g_spell = await card.get_graphical_spell()
		spell_effects = await g_spell.spell_effects()
		return spell_effects

	raise ValueError


async def spell_id_school(spell_id: int, cards: List[CombatCard]) -> int:
	# Returns the school ID for a card corresponding to a spell ID.
	card = await id_to_card(cards, spell_id)

	if card:
		g_spell = await card.get_graphical_spell()
		school_id = await g_spell.magic_school_id()
		return school_id


async def spell_id_school_str(spell_id: int, cards: List[CombatCard]) -> str:
	school_id = await spell_id_school(cards, spell_id)
	return school_to_str(school_id)