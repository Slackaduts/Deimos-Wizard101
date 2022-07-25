import asyncio

from wizwalker import Client, Keycode, XYZ
from wizwalker.extensions.wizsprinter.wiz_navigator import toZone
from wizwalker.memory import Window
from loguru import logger
from src.paths import *
from src.sprinty_client import SprintyClient
from typing import List

async def attempt_activate_mouseless(client: Client, sleep_time: float = 0.1):
	# Attempts to activate mouseless, in a try block in case it's already on for this client
	if not client.mouseless_status:
		try:
			await client.mouse_handler.activate_mouseless()
		except:
			pass
		client.mouseless_status = True
	await asyncio.sleep(sleep_time)


async def attempt_deactivate_mouseless(client: Client, sleep_time: float = 0.1):
	# Attempts to deactivate mouseless, in a try block in case it's already off for this client
	if client.mouseless_status:
		try:
			await client.mouse_handler.deactivate_mouseless()
		except:
			pass
		client.mouseless_status = False
	await asyncio.sleep(sleep_time)


async def get_window_from_path(root_window: Window, name_path: list[str]) -> Window:
	# FULL CREDIT TO SIROLAF FOR THIS FUNCTION
	async def _recurse_follow_path(window, path):
		if len(path) == 0:
			return window
		for child in await window.children():
			if await child.name() == path[0]:
				found_window = await _recurse_follow_path(child, path[1:])
				if not found_window is False:
					return found_window

		return False

	return await _recurse_follow_path(root_window, name_path)


async def is_visible_by_path(client: Client, path: list[str]):
	# FULL CREDIT TO SIROLAF FOR THIS FUNCTION
	# checks visibility of a window from the path
	root = client.root_window
	windows = await get_window_from_path(root, path)
	if windows == False:
		return False
	elif await windows.is_visible():
		return True
	else:
		return False


async def read_control_checkbox_text(checkbox: Window) -> str:
	return await checkbox.read_wide_string_from_offset(616)


# Teleport to given world through spiral door
async def go_to_new_world(p, destinationWorld, open_window: bool = True):
	if open_window:
		while not await get_popup_title(p) == 'World Gate' and not await is_visible_by_path(p, spiral_door_path):
			await asyncio.sleep(0.1)

		while not await is_visible_by_path(p, spiral_door_path):
			await asyncio.sleep(0.1)
			await p.send_key(Keycode.X, 0.1)

	while await p.is_in_npc_range():
		await p.send_key(Keycode.X, 0.1)
		await asyncio.sleep(.4)

	while not await is_visible_by_path(p, spiral_door_path):
		await asyncio.sleep(0.1)
		await p.send_key(Keycode.X, 0.1)

	await p.mouse_handler.activate_mouseless()

	# each worldList item (in-file name for a world) correlates to a zoneDoorOptions (in-file name for the buttons in the spiral door)
	worldList = ["WizardCity", "Krokotopia", "Marleybone", "MooShu", "DragonSpire", "Grizzleheim", "Celestia", "Wysteria", "Zafaria", "Avalon", "Azteca", "Khrysalis", "Polaris", "Arcanum", "Mirage", "Empyrea", "Karamelle", "Lemuria"]
	zoneDoorOptions = ["wbtnWizardCity", "wbtnKrokotopia", "wbtnMarleybone", "wbtnMooShu", "wbtnDragonSpire", "wbtnGrizzleheim", "wbtnCelestia", "wbtnWysteria", "wbtnZafaria", "wbtnAvalon", "wbtnAzteca", "wbtnKhrysalis", "wbtnPolaris", "wbtnArcanum", "wbtnMirage", "wbtnEmpyrea", "wbtnKaramelle", "wbtnLemuria"]
	zoneDoorNameList = ["Wizard City", "Krokotopia", "Marleybone", "MooShu", "DragonSpire", "Grizzleheim", "Celestia", "Wysteria", "Zafaria", "Avalon", "Azteca", "Khrysalis", "Polaris", "Arcanum", "Mirage", "Empyrea", "Karamelle", "Lemuria"]
	# user could be on any of the three pages when opening the world door depending on what their active quest is
	# switch all the way to the first page to standardize it
	for i in range(6):
		await p.mouse_handler.click_window_with_name('leftButton')
		await asyncio.sleep(0.2)

	option_window = await p.root_window.get_windows_with_name("optionWindow")

	assert len(option_window) == 1, str(option_window)

	for child in await option_window[0].children():
		if await child.name() == 'pageCount':
			pageCount = await child.maybe_text()
			pageCount = pageCount[8:-9]
			currentPage = pageCount.split('/', 1)[0]
			maxPage = pageCount.split('/', 1)[1]
			break

	# ensure we are on page 1 (and if not click over again)
	while str(currentPage) != '1':
		await p.mouse_handler.click_window_with_name('leftButton')
		await asyncio.sleep(0.2)
		for child in await option_window[0].children():
			if await child.name() == 'pageCount':
				pageCount = await child.maybe_text()
				pageCount = pageCount[8:-9]
				currentPage = pageCount.split('/', 1)[0]

	worldIndex = worldList.index(destinationWorld)
	spiralGateName = zoneDoorNameList[worldIndex]

	isChildFound = False

	for i in range(int(maxPage)):
		for child in await option_window[0].children():
			if await child.name() in ['opt0', 'opt1', 'opt2', 'opt3']:
				name = await read_control_checkbox_text(child)
				if name == spiralGateName:
					await p.mouse_handler.click_window_with_name(zoneDoorOptions[worldIndex])
					await asyncio.sleep(.4)
					await p.mouse_handler.click_window_with_name('teleportButton')
					await p.wait_for_zone_change()

					await p.mouse_handler.deactivate_mouseless()

					# move away from the spiral door so we dont accidentally click on it again after teleporting later
					await p.send_key(Keycode.W, 1.5)

					isChildFound = True
					break

		# correct world was not found - check the next page
		if not isChildFound:
			previousPage = currentPage
			loopCount = 0
			while currentPage == previousPage and loopCount < 30:
				loopCount += 1
				await p.mouse_handler.click_window_with_name('rightButton')

				# ensure that wizwalker didn't misclick and that we actually changed pages
				for child in await option_window[0].children():
					if await child.name() == 'pageCount':
						pageCount = await child.maybe_text()
						pageCount = pageCount[8:-9]
						currentPage = pageCount.split('/', 1)[0]


async def exit_menus(c):
	path = (exit_recipe_shop_path, exit_equipment_shop_path, cancel_multiple_quest_menu_path, cancel_spell_vendor, exit_snack_shop_path, exit_tc_vendor, exit_minigame_sigil, exit_wysteria_tournament)

	for i in path:
		click_button = await get_window_from_path(c.root_window, i)
		if click_button:
			if await click_button.is_visible():
				await c.mouse_handler.activate_mouseless()
				await c.mouse_handler.click_window(click_button)
				await c.mouse_handler.deactivate_mouseless()


async def click_window_by_path(client: Client, path: list[str], hooks: bool = False):
	# FULL CREDIT TO SIROLAF FOR THIS FUNCTION
	# clicks window from path, must actually exist in the UI tree
	if hooks:
		await attempt_activate_mouseless(client)
	root = client.root_window
	windows = await get_window_from_path(root, path)
	if windows:
		await client.mouse_handler.click_window(windows)
	else:
		await asyncio.sleep(0.1)
	if hooks:
		await attempt_deactivate_mouseless(client)


async def text_from_path(client: Client, path: list[str]) -> str:
	# Returns text from a window via the window path
	window = await get_window_from_path(client.root_window, path)
	return await window.maybe_text()


async def wait_for_loading_screen(client: Client):
	# Wait for a loading screen, then wait until the loading screen has finished.
	logger.debug(f'Client {client.title} - Awaiting loading')
	while not await client.is_loading():
		await asyncio.sleep(0.1)
	while await client.is_loading():
		await asyncio.sleep(0.1)


async def wait_for_zone_change(client: Client, loading_only: bool = False):
	# Wait for zone to change, allows for waiting in team up forever without any extra checks
	logger.debug(f'Client {client.title} - Awaiting loading')
	if not loading_only:
		current_zone = await client.zone_name()
		while current_zone == await client.zone_name():
			await asyncio.sleep(0.1)

	# Second loading check incase theres some sort of phantom zone loading screens put us into
	while await client.is_loading():
		await asyncio.sleep(0.1)


async def spiral_door(client: Client, open_window: bool = True, cycles: int = 0, opt: int = 0):
	# optionally open the spiral door window
	if open_window:
		while not await get_popup_title(client) == 'World Gate' and not await is_visible_by_path(client, spiral_door_path):
			await asyncio.sleep(0.1)

		while not await is_visible_by_path(client, spiral_door_path):
			await asyncio.sleep(0.1)
			await client.send_key(Keycode.X, 0.1)

	# bring menu back to first page
	for i in range(5):
		await client.send_key(Keycode.LEFT_ARROW, 0.1)
		await asyncio.sleep(0.25)

	# navigate menu to proper world
	world_path = spiral_door_path.copy()
	world_path.append(f'opt{opt}')
	await asyncio.sleep(0.5)
	for i in range(cycles):
		if i != 0:
			await client.send_key(Keycode.RIGHT_ARROW, 0.1)
			await asyncio.sleep(0.25)

	await click_window_by_path(client, world_path, True)
	await asyncio.sleep(1)
	await click_window_by_path(client, spiral_door_teleport_path, True)
	await wait_for_zone_change(client)


async def navigate_to_commons(client: Client):
	# navigates to commons from anywhere in the game

	await client.send_key(Keycode.HOME, 0.1)
	await wait_for_zone_change(client)
	use_spiral_door = False
	bartleby_navigation = True
	match await client.zone_name():
		# Handling for dorm room
		case "WizardCity/Interiors/WC_Housing_Dorm_Interior":
			await client.goto(70.15016174316406, 9.419374465942383)
			while not await client.is_loading():
				await client.send_key(Keycode.S, 0.1)
			await wait_for_zone_change(client, True)
			bartleby_navigation = False

		# Handling for arcanum apartment
		case "Housing_AR_Dormroom/Interior":
			while not await client.is_loading():
				await client.send_key(Keycode.S, 0.1)
			await wait_for_zone_change(client, True)
			await asyncio.sleep(0.5)
			await client.teleport(XYZ(x=-19.1153507232666, y=-6312.8994140625, z=-2.00579833984375))
			await client.send_key(Keycode.D, 0.1)
			use_spiral_door = True

		# Any other house in the game
		case _:
			await client.send_key(Keycode.S, 0.1)
			use_spiral_door = True

	# Navigate through spiral door if needed
	if use_spiral_door:
		while not await is_visible_by_path(client, spiral_door_teleport_path):
			await client.send_key(Keycode.X, 0.1)
			await asyncio.sleep(0.25)
		await spiral_door(client)

	# Navigate through bartleby if needed
	if bartleby_navigation:
		await client.goto(-9.711, -2987.212)
		await client.send_key(Keycode.W, 0.1)
		await wait_for_zone_change(client)

	# walk to ravenwood exit
	await client.goto(-19.549846649169922, -297.7527160644531)
	await client.goto(-5.701, -1536.491)
	while not await client.is_loading():
		await client.send_key(Keycode.W, 0.1)
	await wait_for_zone_change(client, True)


async def navigate_to_potions(client: Client):
	# Teleport to hilda brewer
	Hilda_XYZ = XYZ(-4398.70654296875, 1016.1954345703125, 229.00079345703125)
	await client.teleport(Hilda_XYZ)
	await client.send_key(Keycode.S, 0.1)


async def buy_potions(client: Client, recall: bool = True):
	# buy potions and close the potions menu, and recall if needed
	while not await is_visible_by_path(client, potion_shop_base_path):
		await client.send_key(Keycode.X, 0.1)
	await click_window_by_path(client, potion_fill_all_path, True)
	await click_window_by_path(client, potion_buy_path, True)
	while await is_visible_by_path(client, potion_shop_base_path):
		await click_window_by_path(client, potion_exit_path, True)
		await asyncio.sleep(0.5)

	# Put an extra check here in case Starrfox becomes a time traveller or someone is using cheat engine at 100x speed, causing this logic to somehow fail
	if recall and not await client.is_loading():
		await client.send_key(Keycode.PAGE_UP, 0.1)
		await wait_for_zone_change(client)
		await client.send_key(Keycode.PAGE_DOWN, 0.1)


async def to_world(clients, destinationWorld):
	world_hub_zones = ['WizardCity/WC_Hub', 'Krokotopia/KT_Hub', 'Marleybone/MB_Hub', 'MooShu/MS_Hub', 'DragonSpire/DS_Hub_Cathedral', 'Grizzleheim/GH_MainHub', 'Celestia/CL_Hub', 'Wysteria/PA_Hub', 'Zafaria/ZF_Z00_Hub', 'Avalon/AV_Z00_Hub', 'Azteca/AZ_Z00_Zocalo', 'Khrysalis/KR_Z00_Hub', 'Polaris/PL_Z00_Walruskberg', 'Mirage/MR_Z00_Hub', 'Empyrea/EM_Z00_Aeriel_HUB', 'Karamelle/KM_Z00_HUB', 'Lemuria/LM_Z00_Hub']
	world_list = ["WizardCity", "Krokotopia", "Marleybone", "MooShu", "DragonSpire", "Grizzleheim", "Celestia", "Wysteria", "Zafaria", "Avalon", "Azteca", "Khrysalis", "Polaris", "Mirage", "Empyrea", "Karamelle", "Lemuria"]

	world_index = world_list.index(destinationWorld)
	destinationZone = world_hub_zones[world_index]

	zoneChanged = await toZone(clients, destinationZone)

	if zoneChanged == 0:
		logger.debug('Reached destination world: ' + destinationWorld)
	else:
		logger.error('Failed to go to zone.  It may be spelled incorrectly, or may not be supported.')


async def use_potion(client: Client):
	# Uses a potion if we have one
	if await client.stats.potion_charge() >= 1.0:
		logger.debug(f'Client {client.title} - Using potion')
		await click_window_by_path(client, potion_usage_path, True)


async def is_potion_needed(client: Client, minimum_mana: int = 16):
	# Get client stats for mana/hp
	mana = await client.stats.current_mana()
	max_mana = await client.stats.max_mana()
	health = await client.stats.current_hitpoints()
	max_health = await client.stats.max_hitpoints()
	client_level = await client.stats.reference_level()
	if minimum_mana > await client.stats.reference_level():
		minimum_mana = client_level
	combined_minimum_mana = int(0.23 * max_mana) + minimum_mana

	if mana < combined_minimum_mana or float(health) / float(max_health) < 0.55:
		return True
	else:
		return False

async def auto_potions_force_buy(client: Client, mark: bool = False, minimum_mana: int = 16):
	# If we have any missing potions, get potions
	if await client.stats.potion_charge() < await client.stats.potion_max():
		# mark if needed
		if mark:
			await client.send_key(Keycode.PAGE_DOWN, 0.1)
		# Navigate to commons
		await navigate_to_commons(client)
		# Navigate to hilda brewer
		await navigate_to_potions(client)
		# Buy potions
		await buy_potions(client)

		if await is_potion_needed(client, minimum_mana):
			await use_potion(client)

		# Teleport back
		if mark:
			await client.send_key(Keycode.PAGE_UP, 0.1)

async def auto_potions(client: Client, mark: bool = False, minimum_mana: int = 16, buy: bool = True):
	if await is_potion_needed(client, minimum_mana):
		await use_potion(client)
	# If we have less than 1 potion left, get potions
	if await client.stats.potion_charge() < 1.0 and buy:
		# mark if needed
		if mark:
			await client.send_key(Keycode.PAGE_DOWN, 0.1)
		# Navigate to commons
		await navigate_to_commons(client)
		# Navigate to hilda brewer
		await navigate_to_potions(client)
		# Buy potions
		await buy_potions(client)
		# Teleport back
		if mark:
			await client.send_key(Keycode.PAGE_UP, 0.1)

async def wait_for_window_by_path(client: Client, path: list[str], hooks: bool = False, click: bool = True):
	while not await is_visible_by_path(client, path):
		await asyncio.sleep(0.1)
	if click or hooks:
		await click_window_by_path(client, path, hooks)


async def logout_and_in(client: Client):
	# Improved version of Major's logging out and in function
	await client.send_key(Keycode.ESC, 0.1)
	await wait_for_window_by_path(client, quit_button_path, True)
	await asyncio.sleep(0.25)
	if await is_visible_by_path(client, dungeon_warning_path):
		await client.send_key(Keycode.ENTER, 0.1)
	await wait_for_window_by_path(client, play_button_path, True)
	# TODO: Find a better solution to waiting for load in screen to end
	await asyncio.sleep(4)
	if await client.is_loading():
		await wait_for_loading_screen(client)


async def is_free(client: Client):
	# Returns True if not in combat, loading screen, or in dialogue.
	return not any([await client.is_loading(), await client.in_battle(), await is_visible_by_path(client, advance_dialog_path)])


async def get_quest_name(client: Client):
	while not await is_free(client):
		await asyncio.sleep(0.1)
	quest_name_window = await get_window_from_path(client.root_window, quest_name_path)
	while not await is_visible_by_path(client, quest_name_path):
		await asyncio.sleep(0.1)
	quest_objective = await quest_name_window.maybe_text()
	quest_objective = quest_objective.replace('<center>', '')
	quest_objective = quest_objective.replace('</center>', '')
	return quest_objective


async def get_popup_title(client: Client) -> str:
	if await is_visible_by_path(client, popup_title_path):
		# popup_str = str(await get_window_from_path(client.root_window, popup_title_path))
		popup_window = await get_window_from_path(client.root_window, popup_title_path)
		popup_str = await popup_window.maybe_text()

		try:
			popup_str = popup_str.replace('<center>', '')
			popup_str = popup_str.replace('</center>', '')
		except:
			await asyncio.sleep(0.1)

		return popup_str

	else:
		return None


async def is_popup_title_relevant(client: Client, quest_info: str = None) -> bool:
	if not quest_info:
		quest_info = await get_quest_name(client)

	popup_text = await get_window_from_path(client.root_window, popup_title_path)
	maybe_collect_item = await popup_text.maybe_text()
	if maybe_collect_item.lower() in str(quest_info).lower():
		return True
	return False


async def spiral_door_with_quest(client: Client):
	while await is_visible_by_path(client, spiral_door_teleport_path):
		await click_window_by_path(client, spiral_door_teleport_path, True)
		await asyncio.sleep(0.25)

	while await client.is_loading():
		await asyncio.sleep(0.1)


async def collect_wisps(client: Client):
	# Collects all the wisps in the current area, only works within the entity draw distance.
	entities= []
	entities = await SprintyClient(client).get_base_entities_with_vague_name('WispHealth')
	entities += await SprintyClient(client).get_base_entities_with_vague_name('WispHealth')
	entities += await SprintyClient(client).get_base_entities_with_vague_name('WispGold')

	safe_entities = await SprintyClient(client).find_safe_entities_from(entities)

	if safe_entities:
		for entity in safe_entities:
			wisp_xyz = await entity.location()
			await client.teleport(wisp_xyz)
			await asyncio.sleep(0.1)


async def pid_to_client(clients: List[Client], pid: int) -> Client:
	for client in clients:
		if client.process_id == pid:
			return client

	if clients:
		return clients[0]
	else:
		return None