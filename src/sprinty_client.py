from wizwalker import Client, MemoryReadError, XYZ
from wizwalker.memory import DynamicClientObject
from typing import *



class SprintyClient():
	# FULL CREDIT TO SIROLAF FOR THIS CLASS
	def __init__(self, client: Client):
		self.client = client


	async def remove_excluded_entities_from(self, entities: List[DynamicClientObject], excluded_ids: Set[int] = None) \
			-> List[DynamicClientObject]:
		if excluded_ids is not None and len(excluded_ids) > 0:
			res = []
			for e in entities:
				if excluded_ids is None or await e.global_id_full() not in excluded_ids:
					res.append(e)
			return res
		return entities


	async def get_base_entity_list(self, excluded_ids: Set[int] = None) -> List[DynamicClientObject]:
		return await self.remove_excluded_entities_from(await self.client.get_base_entity_list(), excluded_ids)


	async def get_base_entities_with_predicate(self, predicate: Callable, excluded_ids: Set[int] = None):
		entities = []

		for entity in await self.get_base_entity_list(excluded_ids):
			if await predicate(entity):
				entities.append(entity)

		return entities


	async def get_base_entities_with_name(self, name: str, excluded_ids: Set[int] = None):
		return await self.remove_excluded_entities_from(await super().get_base_entities_with_name(name), excluded_ids)


	async def get_base_entities_with_vague_name(self, name: str, excluded_ids: Set[int] = None) -> List[DynamicClientObject]:
		async def _pred(e):
			if temp := await e.object_template():
				return name.lower() in (await temp.object_name()).lower()
			return False

		return await self.get_base_entities_with_predicate(_pred, excluded_ids)


	async def get_base_entities_with_behaviors(self, behaviors: List[str], excluded_ids: Set[int] = None):
		res = []
		for entity in await self.get_base_entity_list(excluded_ids):
			good = True
			try:
				inactive_behaviors = [await beh.read_type_name() for beh in await entity.inactive_behaviors()]
				for behavior in behaviors:
					if behavior not in inactive_behaviors:
						good = False
						break
				if good:
					res.append(entity)
			except (ValueError, MemoryReadError):
				continue
		return res


	async def get_health_wisps(self, excluded_ids: Set[int] = None) -> List[DynamicClientObject]:
		return await self.get_base_entities_with_vague_name("WispHealth", excluded_ids)


	async def get_mana_wisps(self, excluded_ids: Set[int] = None) -> List[DynamicClientObject]:
		return await self.get_base_entities_with_vague_name("WispMana", excluded_ids)


	async def get_gold_wisps(self, excluded_ids: Set[int] = None) -> List[DynamicClientObject]:
		return await self.get_base_entities_with_vague_name("WispGold", excluded_ids)


	async def get_mobs(self, excluded_ids: Set[int] = None) -> List[DynamicClientObject]:
		async def _pred(e: DynamicClientObject):
			try:
				behaviors = await e.inactive_behaviors()
				for b in behaviors:
					if (await b.read_type_name()) == "NPCBehavior":
						return await b.read_value_from_offset(288, "bool")
				return False
			except (ValueError, MemoryReadError):
				return False
		return await self.get_base_entities_with_predicate(_pred, excluded_ids)


	async def find_safe_entities_from(self, entities: List[DynamicClientObject], safe_distance: float = 2000) \
			-> List[DynamicClientObject]:
		mob_positions = []
		a = (await self.client.stats.current_gold())
		for mob in await self.get_mobs():
			mob_positions.append(await mob.location())


		safe = []
		for entity in entities:
			pos = await entity.location()
			good = True
			for p in mob_positions:
				if p.distance(pos) < safe_distance:
					good = False
					break
			if good:
				safe.append(entity)

		return safe


	async def find_closest_of_entities(self, entities: List[DynamicClientObject], only_safe: bool = False) \
			-> Optional[DynamicClientObject]:
		closest = None
		smallest_dist = 0
		self_pos = await self.client.body.position()
		if only_safe:
			entities = await self.find_safe_entities_from(entities)
		for w in entities:
			dist = self_pos.distance(await w.location())
			if closest is None or dist < smallest_dist:
				smallest_dist = dist
				closest = w
		return closest


	async def find_closest_by_predicate(self, pred: Callable, only_safe: bool = False, excluded_ids: Set[int] = None) -> Optional[DynamicClientObject]:
		return await self.find_closest_of_entities(await self.get_base_entities_with_predicate(pred, excluded_ids), only_safe)


	async def find_closest_by_name(self, name: str, only_safe: bool = False, excluded_ids: Set[int] = None) -> Optional[DynamicClientObject]:
		return await self.find_closest_of_entities(await self.get_base_entities_with_name(name, excluded_ids), only_safe)


	async def find_closest_by_vague_name(self, name: str, only_safe: bool = False, excluded_ids: Set[int] = None) -> Optional[DynamicClientObject]:
		return await self.find_closest_of_entities(await self.get_base_entities_with_vague_name(name, excluded_ids), only_safe)


	async def find_closest_health_wisp(self, only_safe: bool = False, excluded_ids: Set[int] = None) -> Optional[DynamicClientObject]:
		return await self.find_closest_of_entities(await self.get_health_wisps(excluded_ids), only_safe)


	async def find_closest_mana_wisp(self, only_safe: bool = False, excluded_ids: Set[int] = None) -> Optional[DynamicClientObject]:
		return await self.find_closest_of_entities(await self.get_mana_wisps(excluded_ids), only_safe)


	async def find_closest_gold_wisp(self, only_safe: bool = False, excluded_ids: Set[int] = None) -> Optional[DynamicClientObject]:
		return await self.find_closest_of_entities(await self.get_gold_wisps(excluded_ids), only_safe)


	async def find_closest_mob(self, excluded_ids: Set[int] = None) -> Optional[DynamicClientObject]:
		return await self.find_closest_of_entities(await self.get_mobs(excluded_ids), False)


	async def tp_to(self, entity: DynamicClientObject) -> bool:
		if entity is not None:
			try:
				await self.client.teleport(await entity.location())
				return True
			except (ValueError, MemoryReadError):
				return False
		return False


	async def tp_to_closest_of(self, entities: List[DynamicClientObject], only_safe: bool = False):
		if e := await self.find_closest_of_entities(entities, only_safe):
			await self.client.teleport(await e.location())
			return True
		return False


	async def tp_to_closest_by_name(self, name: str, only_safe: bool = False, excluded_ids: Set[int] = None) -> bool:
		if e := await self.find_closest_by_name(name, only_safe, excluded_ids):
			await self.client.teleport(await e.location())
			return True
		return False


	async def tp_to_closest_by_vague_name(self, name: str, only_safe: bool = False, excluded_ids: Set[int] = None) -> bool:
		if e := await self.find_closest_by_vague_name(name, only_safe, excluded_ids):
			await self.client.teleport(await e.location())
			return True
		return False


	async def tp_to_closest_health_wisp(self, only_safe: bool = False,
										excluded_ids: Set[int] = None) -> bool:
		return await self.tp_to_closest_of(await self.get_health_wisps(excluded_ids), only_safe)


	async def tp_to_closest_mana_wisp(self, only_safe: bool = False, excluded_ids: Set[int] = None) -> bool:
		return await self.tp_to_closest_of(await self.get_mana_wisps(excluded_ids), only_safe)


	async def tp_to_closest_gold_wisp(self, only_safe: bool = False, excluded_ids: Set[int] = None) -> bool:
		return await self.tp_to_closest_of(await self.get_gold_wisps(excluded_ids), only_safe)


	async def tp_to_closest_mob(self, excluded_ids: Set[int] = None) -> bool:
		return await self.tp_to_closest_of(await self.get_mobs(excluded_ids), False)


	async def calc_health_ratio(self) -> float:
		"""Simply returns current health divided by max health"""
		return await self.client.stats.current_hitpoints() / await self.client.stats.max_hitpoints()


	async def calc_mana_ratio(self) -> float:
		"""Simply returns current health divided by max health"""
		return await self.client.stats.current_mana() / await self.client.stats.max_mana()


	async def needs_health(self, health_percent: int = 20) -> bool:
		return await self.calc_health_ratio() * 100 <= health_percent


	async def needs_mana(self, mana_percent: int = 10) -> bool:
		return await self.calc_mana_ratio() * 100 <= mana_percent


	async def has_potion(self) -> bool:
		return await self.client.stats.potion_charge() >= 1.0


	async def use_potion(self, handle_hooks: bool = False) -> bool:
		if await self.has_potion():
			async with self.client.mouse_handler:
				try:
					await self.client.mouse_handler.click_window_with_name("btnPotions")
				except ValueError:
					return False
			return True
		return False


	async def needs_potion(self, health_percent: int = 20, mana_percent: int = 10) -> bool:
		return await self.needs_health(health_percent) or await self.needs_mana(mana_percent)


	async def use_potion_if_needed(self, health_percent: int = 20, mana_percent: int = 10, handle_hooks: bool = False) -> bool:
		"""
		:param health_percent: How low health needs to be in percent
		:param mana_percent: How low mana needs to be in percent
		:return: False if it needed a potion but doesn't have any and True if it needed no potion or used one
		"""
		if await self.needs_potion(health_percent, mana_percent):
			return await self.use_potion(handle_hooks)
		return True