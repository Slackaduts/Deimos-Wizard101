import asyncio
from src.teleport_math import calc_Distance, navmap_tp, calc_chunks, get_navmap_data
from wizwalker import XYZ, Keycode, MemoryReadError, Client
from wizwalker.memory import DynamicClientObject
from src.sprinty_client import SprintyClient
from src.utils import auto_potions, get_quest_name, click_window_by_path, is_popup_title_relevant, is_visible_by_path, is_free, is_popup_title_relevant, spiral_door_with_quest, is_potion_needed, collect_wisps
from src.paths import cancel_chest_roll_path, npc_range_path, missing_area_path, missing_area_retry_path, spiral_door_teleport_path, team_up_button_path, dungeon_warning_path
from difflib import SequenceMatcher


class Quester():
	def __init__(self, client: Client, clients: list[Client], leader_pid: int):
		self.client = client
		self.clients = clients
		self.leader_pid = leader_pid
		# TODO: Make auto questing accept an optional XYZ param so we can have team based questing


	async def auto_quest(self):
		while self.client.questing_status:
			await asyncio.sleep(1)

			if await is_free(self.client):
				if await is_potion_needed(self.client) and await self.client.stats.current_mana() > 1 and await self.client.stats.current_hitpoints() > 1:
					await collect_wisps(self.client)

				await auto_potions(self.client, True, buy = True)
				quest_xyz = await self.client.quest_position.position()

				if quest_xyz != XYZ(0.0, 0.0, 0.0):
					await navmap_tp(self.client, quest_xyz)

					await asyncio.sleep(0.25)
					if await is_visible_by_path(self.client, cancel_chest_roll_path):
						# Handles chest reroll menu, will always cancel
						await click_window_by_path(self.client, cancel_chest_roll_path)

					current_pos = await self.client.body.position()
					if await is_visible_by_path(self.client, npc_range_path) and calc_Distance(quest_xyz, current_pos) < 750.0:
						# Handles interactables
						if await is_visible_by_path(self.client, team_up_button_path):
							# Handles entering sigils
							await self.client.send_key(Keycode.X, 0.1)
							while not await self.client.is_loading():
								if await is_visible_by_path(self.client, dungeon_warning_path):
									await self.client.send_key(Keycode.ENTER, 0.1)
								await asyncio.sleep(0.1)

							while await self.client.is_loading():
								await asyncio.sleep(0.1)
						else:
							await self.client.send_key(Keycode.X, 0.1)
							await asyncio.sleep(0.75)
							if await is_visible_by_path(self.client, spiral_door_teleport_path):
								# Handles spiral door navigation
								await spiral_door_with_quest(self.client)

					quest_objective = await get_quest_name(self.client)

					if "Photomance" in quest_objective:
						# Photomancy quests (WC, KM, LM)
						await self.client.send_key(key=Keycode.Z, seconds=0.1)
						await self.client.send_key(key=Keycode.Z, seconds=0.1)

					if await is_visible_by_path(self.client, missing_area_path):
						# Handles when an area hasn't been downloaded yet
						while not await is_visible_by_path(self.client, missing_area_retry_path):
							await asyncio.sleep(0.1)
						await click_window_by_path(self.client, missing_area_retry_path, True)

				else:
					await self.handle_collect_quest()


	async def handle_sigil_wait(self, min_sigil_distance: float = 750.0):
		sprinter = SprintyClient(self.client)
		sigils = await sprinter.get_base_entities_with_name('Teleport Semi Circle 4 Player Generic')

		if sigils:
			nearest_sigil = await sprinter.find_closest_of_entities(sigils)
			nearest_sigil_pos = await nearest_sigil.location()
			current_pos = await self.client.body.position()
			current_zone = await self.client.zone_name()
			if calc_Distance(nearest_sigil_pos, current_pos) < min_sigil_distance:
				while current_zone == await self.client.zone_name():
					if await is_visible_by_path(self.client, missing_area_path):
						while not await is_visible_by_path(self.client, missing_area_retry_path):
							await asyncio.sleep(0.1)
						await click_window_by_path(self.client, missing_area_retry_path, True)

					await asyncio.sleep(0.1)


	async def handle_collect_quest(self):
		print(1)
		navmap_points = await get_navmap_data(self.client)
		print(2)
		current_pos = await self.client.body.position()
		print(3)
		adjusted_pos = XYZ(current_pos.x, current_pos.y, current_pos.z - 350)
		print(4)
		chunks = calc_chunks(navmap_points, adjusted_pos)

		print(5)
		quest_objective = await get_quest_name(self.client)
		print(6)

		sprinter = SprintyClient(self.client)
		for chunk in chunks:
			if await is_free(self.client) and self.client.questing_status:
				# await navmap_tp(self.client, chunk)
				await self.client.teleport(chunk, wait_on_inuse = True)

			await asyncio.sleep(1)

			entities = await sprinter.get_base_entity_list()
			safe_entities = await sprinter.find_safe_entities_from(entities, safe_distance=2600)
			relevant_str = await self.parse_quest_objective()
			relevant_entities = await self.relevant_named_entities(safe_entities, relevant_str)

			if relevant_entities:
				await self.check_entities(relevant_entities, relevant_str)

			if await get_quest_name(self.client) != quest_objective:
				quest_xyz = await self.client.quest_position.position()
				if quest_xyz != XYZ(0.0, 0.0, 0.0):
					break

			else:
				await self.check_entities(safe_entities, relevant_str)


	async def check_entities(self, entities: list[DynamicClientObject], relevant_str: str, pet_mode: bool = False):
		quest_objective = await get_quest_name(self.client)
		for entity in entities:
			entity_pos = await entity.location()

			if not pet_mode:
				await self.client.teleport(entity_pos)
			else:
				await self.client.pet_teleport(entity_pos)

			await asyncio.sleep(0.25)

			if await get_quest_name(self.client) != quest_objective:
				quest_pos = await self.client.quest_position.position()
				if quest_pos != XYZ(0.0, 0.0, 0.0):
					break

			elif await is_visible_by_path(self.client, npc_range_path):
				if await is_popup_title_relevant(self.client, relevant_str):
					await self.client.send_key(Keycode.X, 0.1)
					await asyncio.sleep(0.25)


	async def parse_quest_objective(self) -> str:
		objective_str = await get_quest_name(self.client)
		objective_list = objective_str.split(' ')
		if objective_list:
			objective_list = [s.lower() for s in objective_list.copy()]
			collect_keywords = ['collect', 'get', 'gather', 'find', 'obtain', 'use', 'open', 'locate', 'destroy']
			if len(objective_list) >= 2:
				for i, collect_str in enumerate(collect_keywords):
					if collect_str in objective_list:
						if len(objective_list) >= i + 2:
							return objective_list[i + 1]

			return objective_list[0]


	async def relevant_named_entities(self, entities: list[DynamicClientObject], relevant_str: str) -> list[DynamicClientObject]:
		for entity in entities.copy():
			try:
				object_template = await entity.object_template()
				display_name_code = await object_template.display_name()
				try:
					display_name: str = await self.client.cache_handler.get_langcode_name(display_name_code)
				except ValueError:
					display_name = await object_template.object_name()
				
				if 'Basic' not in display_name:
					match_ratio = SequenceMatcher(None, display_name.lower(), relevant_str.lower()).ratio()

					if match_ratio > 0.7:
						pass
					else:
						entities.remove(entity)

				else:
					entities.remove(entity)

			except MemoryReadError:
				await asyncio.sleep(0.05)
			except AttributeError:
				await asyncio.sleep(0.05)
			except ValueError:
				pass

		return entities