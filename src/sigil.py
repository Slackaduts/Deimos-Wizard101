import asyncio
from wizwalker import Keycode, Client, XYZ
from loguru import logger
from src.teleport_math import navmap_tp, calc_FrontalVector, are_xyzs_within_threshold
from src.utils import is_visible_by_path, click_window_by_path, wait_for_zone_change, auto_potions, logout_and_in, is_free, get_quest_name, collect_wisps
from src.paths import team_up_button_path, team_up_confirm_path, dungeon_warning_path, cancel_chest_roll_path, npc_range_path
from src.sprinty_client import SprintyClient


class Sigil():
	def __init__(self, client: Client, clients: list[Client], leader_pid: int):
		self.client = client
		self.clients = clients
		self.leader_pid = leader_pid


	async def record_sigil(self):
		self.sigil_xyz = await self.client.body.position()
		self.sigil_zone = await self.client.zone_name()
		# mark location
		await self.client.send_key(Keycode.PAGE_DOWN, 0.1)


	async def record_quest(self):
		self.original_quest = await get_quest_name(self.client)


	async def team_up(self):
		# Wait for team up to be visible in case it isnt
		while not await is_visible_by_path(self.client, team_up_button_path):
			await asyncio.sleep(0.25)
		# click team up button
		await click_window_by_path(self.client, team_up_button_path, True)
		await asyncio.sleep(0.5)
		if await is_visible_by_path(self.client, team_up_confirm_path):
			await click_window_by_path(self.client, team_up_confirm_path, True)
			while not await self.client.is_loading():
				await asyncio.sleep(0.1)
			await wait_for_zone_change(self.client, True)
		else:
			while not await self.client.is_loading():
				await asyncio.sleep(0.1)
			await wait_for_zone_change(self.client, True)


	async def join_sigil(self):
		# joins sigil using
		if self.client.use_team_up:
			await self.team_up()
		else:
			await self.client.send_key(Keycode.X, seconds=0.1)
			await asyncio.sleep(0.5)
			if await is_visible_by_path(self.client, dungeon_warning_path):
				await self.client.send_key(Keycode.ENTER, 0.1)
			await wait_for_zone_change(self.client)


	async def go_through_zone_changes(self):
		while await self.client.zone_name() != self.sigil_zone:
			# teleport to quest, will NOT work if the user has no quest up
			quest_xyz = await self.client.quest_position.position()
			await navmap_tp(self.client, quest_xyz)

			# walk forward until we get a zone change
			while not await self.client.is_loading():
				await self.client.send_key(Keycode.W, seconds=0.1)
			await wait_for_zone_change(self.client, True)
			await asyncio.sleep(1)


	async def wait_for_combat_finish(self, await_combat: bool = True, should_collect_wisps: bool = True):
		if await_combat:
			while not await self.client.in_battle():
				await asyncio.sleep(0.1)
		while await self.client.in_battle():
			await asyncio.sleep(0.1)
		if should_collect_wisps:
			await collect_wisps(self.client)


	async def movement_checked_teleport(self, xyz: XYZ):
		current_xyz = await self.client.body.position()
		frontal_xyz = await calc_FrontalVector(client=self.client, speed_constant=200, speed_adjusted=False)
		await self.client.goto(frontal_xyz)
		if not await are_xyzs_within_threshold(current_xyz, await self.client.body.position(), threshold=20):
			await self.client.teleport(xyz)


	async def wait_for_sigil(self):
		# Waits for the client to walk near a sigil
		while self.client.sigil_status:
			await asyncio.sleep(0.25)
			if not await is_visible_by_path(self.client, team_up_button_path):
				pass

			else:
				await self.farm_sigil()


	async def solo_farming_logic(self):
		while self.client.sigil_status:
			while not await is_visible_by_path(self.client, team_up_button_path) and self.client.sigil_status:
				await asyncio.sleep(0.1)

			# Automatically use and buy potions if needed
			await auto_potions(self.client)

			# Join sigil and wait for the zone to change either via team up or sigil countdown
			await self.join_sigil()
			
			# if quest objective is same, we know it's a short dungeon, most likely with 1 room
			if await get_quest_name(self.client) == self.original_quest:
				start_xyz = await self.client.body.position() 
				second_xyz = await calc_FrontalVector(self.client, speed_constant=200, speed_adjusted=False)
				await SprintyClient(self.client).tp_to_closest_mob()

				await self.wait_for_combat_finish()

				await asyncio.sleep(0.1)

				after_xyz = await calc_FrontalVector(self.client, speed_constant=450, speed_adjusted=False)

				await collect_wisps(self.client)

				await self.client.teleport(after_xyz)
				await asyncio.sleep(0.1)
				while True:
					await self.client.goto(second_xyz.x, second_xyz.y)
					await asyncio.sleep(0.1)
					await self.client.goto(start_xyz.x, start_xyz.y)
					past_zone_change_xyz = await calc_FrontalVector(self.client, speed_adjusted=False)
					await self.client.goto(past_zone_change_xyz.x, past_zone_change_xyz.y)
					counter = 0
					while not await self.client.is_loading() and counter < 35:
						await asyncio.sleep(0.1)
						counter += 1
					if counter >= 35:
						await self.client.teleport(after_xyz)
						pass
					else:
						break

				logger.debug(f'Client {self.client.title} - Awaiting loading')
				while await self.client.is_loading():
					await asyncio.sleep(0.1)

			else:
				# TODO: Logic for dungeons with questlines
				while self.client.sigil_status:
					await asyncio.sleep(1)
					if await is_free(self.client):
						quest_xyz = await self.client.quest_position.position()
						if await get_quest_name(self.client) != self.original_quest:
							try:
								await navmap_tp(self.client, quest_xyz)
							except ValueError:
								pass

						await asyncio.sleep(0.25)

						if await is_visible_by_path(self.client, cancel_chest_roll_path):
							click_window_by_path(self.client, cancel_chest_roll_path)

						if await is_visible_by_path(self.client, npc_range_path):
							await self.client.send_key(Keycode.X, 0.1)

						if await get_quest_name(self.client) == self.original_quest:
							await asyncio.sleep(1)
							break

				while not await is_free(self.client) and self.client.sigil_status:
					await asyncio.sleep(0.1)
				await logout_and_in(self.client)

			while not await is_free(self.client) and self.client.sigil_status:
				await asyncio.sleep(0.1)

			if self.client.sigil_status:
				await asyncio.sleep(1)
				await self.client.teleport(self.sigil_xyz)
				await self.client.send_key(Keycode.A, 0.1)


	async def follower_farming_logic(self):

		while self.client.sigil_status:
			await asyncio.sleep(0.1)

			while self.client.sigil_status and await is_free(self.client):
				leader_pos = await self.leader.body.position()
				await self.client.teleport(leader_pos)
				await asyncio.sleep(0.05)


	async def farm_sigil(self):
		# Main loop for farming a sigil, includes setup
		logger.debug(f'Client {self.client.title} at sigil, farming it.')
		await self.record_sigil()
		await self.record_quest()

		if self.leader_pid:
			self.leader: Client = None

			# Determines what client the leader is
			for client in self.clients:
				if client.process_id == self.leader_pid:
					self.leader = client
					break

			if self.leader.process_id == self.client.process_id:
				await self.solo_farming_logic()

			else:
				# TODO: Somehow finish this function
				await self.follower_farming_logic()

		else:
			await self.solo_farming_logic()
