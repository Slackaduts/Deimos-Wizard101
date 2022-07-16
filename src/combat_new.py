from typing import List, Tuple
from wizwalker import Client, utils
from wizwalker.errors import ExceptionalTimeout
from wizwalker.combat import CombatHandler, CombatCard, CombatMember
from wizwalker.memory.memory_objects.spell_effect import DynamicSpellEffect
from wizwalker.memory.memory_objects.enums import SpellEffects
from src.combat_objects import get_school_stat, get_game_stats, get_shadow_effects, get_hanging_effects, get_aura_effects


hit_enchant_effects = [SpellEffects.modify_card_damage, SpellEffects.modify_card_accuracy, SpellEffects.modify_card_armor_piercing]

enchant_effects = {
	'AOE': hit_enchant_effects,
	'Damage': hit_enchant_effects,
	'Steal': hit_enchant_effects,
	'Heal': [SpellEffects.modify_card_heal],
	'Charm': [SpellEffects.modify_card_outgoing_damage],
	'Ward': [SpellEffects.modify_card_incoming_damage]
}

total_enchant_effects = [v for _, v in enchant_effects.items()]



class Fighter(CombatHandler):
	def __init__(self, client: Client, clients: list[Client]):
		self.client = client
		self.clients = clients
		self.card_ids: List[CombatCard] = []
		self.duel_status = 'pve'


	async def get_cards(self) -> List[CombatCard]:  # extended to sort by enchanted # Olaf's fix for coro graphical spell error
			async def _inner() -> List[CombatCard]:
				cards = await super(Fighter, self).get_cards()
				rese, res = [], []
				for card in cards:
					if await card.is_enchanted():
						rese.append(card)
					else:
						res.append(card)
				return rese + res
			try:
				return await utils.maybe_wait_for_any_value_with_timeout(_inner, sleep_time=0.2, timeout=2.0)
			except ExceptionalTimeout:
				return []


	async def get_card_ids(self, cards: List[CombatCard] = None) -> List[int]:
		if not cards:
			await self.get_cards()
		
		ids = []
		for card in cards:
			id = await card.spell_id()
			ids.append(id)

		return ids


	async def member_from_id(self, id: int, members: List[CombatMember] = None) -> CombatMember:
		if not members:
			members = await self.get_members()

		for member in members:
			if await member.owner_id() == id:
				return member

		raise ValueError


	async def effects_from_id(self, id: int, cards: List[CombatCard] = None) -> List[DynamicSpellEffect]:
		'''Gets the CombatCard corresponding to a specific spell ID, and returns its SpellEffects'''
		if not cards:
			cards = await self.get_cards()

		for card in cards:
			if await card.spell_id() == id:
				g_spell = await card.get_graphical_spell()
				spell_effects = await g_spell.spell_effects()
				return spell_effects

		raise ValueError


	async def effect_types_from_id(self, id: int, cards: List[CombatCard] = None) -> List[SpellEffects]:
		'''Gets the CombatCard corresponding to a specific spell ID, and returns its SpellEffects types'''
		if not cards:
			cards = await self.get_cards()

		for card in cards:
			if await card.spell_id() == id:
				g_spell = await card.get_graphical_spell()
				spell_effects = await g_spell.spell_effects()
				effect_types: List[SpellEffects] = [await e.effect_type() for e in spell_effects]
				return effect_types

		raise ValueError


	async def card_from_id(self, id: int, cards: List[CombatCard] = None) -> CombatCard:
		'''Returns the CombatCard corresponding to a specific spell ID'''
		if not cards:
			cards = await self.get_cards()

		for card in cards:
			if await card.spell_id() == id:
				return card

		raise ValueError


	async def is_enchantable(self, card: CombatCard) -> bool:
		return not any([await card.is_enchanted(), await card.is_item_card(), await card.is_cloaked(), await card.is_treasure_card()])


	async def assign_enchants(self, cards: List[CombatCard] = None) -> Tuple[List[int], List[int]]:
		'''Takes in a list of cards and returns a tuple with a list of the IDs of those that are enchants, and another with those that are not.'''
		if not cards:
			cards = await self.get_cards()

		enchant_ids = []
		non_enchant_ids = []

		for card_id in self.card_ids:
			card = await self.card_from_id(card_id, cards)

			if await card.type_name() == 'Enchantment':
				spell_effects = await self.effect_types_from_id(card_id, cards)
				for effect in spell_effects:
					if effect in total_enchant_effects:
						enchant_ids.append(card_id)
						break

				else:
					non_enchant_ids.append(card_id)

			else:
				non_enchant_ids.append(card_id)

		return Tuple[enchant_ids, non_enchant_ids]


	async def enchant_available_cards(self):
		'''Enchants all possible cards.'''
		cards = await self.get_cards()

		enchant_ids, non_enchant_ids = await self.assign_enchants(cards)
		valid_types_for_id = {}

		for card_id in non_enchant_ids:
			card = await self.card_from_id(card_id, cards)
			card_type = await card.type_name()
			if card_type in enchant_effects and await self.is_enchantable(card):
				valid_types_for_id[card_id] = enchant_effects[card_id]

		used_enchant_ids = []

		for card_id in valid_types_for_id:
			matching_enchant_types = valid_types_for_id[card_id]

			for e_id in enchant_ids:
				spell_effects = await self.effect_types_from_id(e_id)

				if any([effect in matching_enchant_types for effect in spell_effects]) and e_id not in used_enchant_ids:
					cards = await self.get_cards()
					enchant = await self.card_from_id(e_id, cards)
					card = await self.card_from_id(card_id, cards)
					await enchant.cast(card, sleep_time=0.1)
					used_enchant_ids.append(e_id)
					break