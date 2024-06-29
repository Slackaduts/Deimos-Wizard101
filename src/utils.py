import asyncio
import ctypes
import time
import traceback
import requests

import wizwalker.errors
from wizwalker import Client, Keycode, XYZ, kernel32
from wizwalker.utils import get_all_wizard_handles, override_wiz_install_location, get_pid_from_handle
from wizwalker.extensions.scripting.utils import _maybe_get_named_window, _cycle_to_online_friends, _click_on_friend, _teleport_to_friend, _friend_list_entry
from wizwalker.extensions.wizsprinter.wiz_navigator import toZone
from wizwalker.memory import Window, WindowFlags
from wizwalker.combat import CombatMember
from loguru import logger

from src.dance_game_hook import attempt_deactivate_dance_hook
from src.paths import *
from src.sprinty_client import SprintyClient
import typing
from typing import List, Optional, Coroutine, Union, get_type_hints, Any, Iterable
from enum import Enum

import os
import yaml

import inspect
import ast

# from src.teleport_math import calc_Distance

streamportal_locations = ["aeriel", "zanadu", "outer athanor", "inner athanor", "sepidious", "mandalla", "chaos jungle", "reverie", "nimbus", "port aero", "husk"]
nanavator_locations = ["karamelle city", "sweetzburg", "nibbleheim", "gutenstadt", "black licorice forest", "candy corn farm", "gobblerton"]

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

    async with p.mouse_handler:
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

                        # move away from the spiral door so we dont accidentally click on it again after teleporting later
                        # await p.send_key(Keycode.W, 1.5)

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

async def new_portals_cycle( client: Client, location: str):
        option_window = await client.root_window.get_windows_with_name("optionWindow")
        assert len(option_window) == 1, str(option_window)
        for child in await option_window[0].children():
            if await child.name() == 'pageCount':
                pageCount = await child.maybe_text()
                pageCount = pageCount[8:-9]
                currentPage = pageCount.split('/', 1)[0]
                maxPage = pageCount.split('/', 1)[1]
                break
            
        spiralGateName = location

        isChildFound = False

        for _ in range(int(maxPage)):
            for child in await option_window[0].children():
                if await child.name() in ['opt0', 'opt1', 'opt2', 'opt3']:
                    name = await read_control_checkbox_text(child)
                    if name.lower() == spiralGateName.lower():
                        async with client.mouse_handler:
                            await client.mouse_handler.click_window_with_name(await child.name())
                            await asyncio.sleep(.4)
                            await client.mouse_handler.click_window_with_name('teleportButton')
                            await client.wait_for_zone_change()

                        isChildFound = True
                        break

            # correct world was not found - check the next page
            if not isChildFound:
                previousPage = currentPage
                loopCount = 0
                while currentPage == previousPage and loopCount < 30:
                    loopCount += 1
                    async with client.mouse_handler:
                        await client.mouse_handler.click_window_with_name('rightButton')
                    # ensure that wizwalker didn't misclick and that we actually changed pages
                    for child in await option_window[0].children():
                        if await child.name() == 'pageCount':
                            pageCount = await child.maybe_text()
                            pageCount = pageCount[8:-9]
                            currentPage = pageCount.split('/', 1)[0]

async def generate_tfc(client: Client):
    async with client.mouse_handler:
        # This fails consistently, even when the friends list is actually open.  Detecting whether the friends list is open is also horrifically inconsistent so just brute force it
        for i in range(5):
            try:
                await click_window_by_path(client, close_real_friend_list_button_path)
                await asyncio.sleep(.1)
            except ValueError:
                await asyncio.sleep(.1)

        for i in range(2):
            await client.send_key(Keycode.F, 0.1)
            await asyncio.sleep(.2)

        if await is_visible_by_path(client, enter_true_friend_code_button_path):
            await click_window_by_path(client, enter_true_friend_code_button_path)

        await asyncio.sleep(.3)

        if await is_visible_by_path(client, generate_true_friend_code_path):
            await click_window_by_path(client, generate_true_friend_code_path)

        await asyncio.sleep(1.0)

        try:
            tfc_window = await get_window_from_path(client.root_window, true_friend_code_text_path)
            tfc = await tfc_window.maybe_text()
        except:
            print(traceback.print_exc())
            tfc = None

        if await is_visible_by_path(client, exit_generate_true_friend_window):
            await click_window_by_path(client, exit_generate_true_friend_window)

    print(tfc)
    return tfc


# UNFINISHED - requires some way to type in wiz's edit texts
async def accept_tfc(client: Client, tfc: str):
    async with client.mouse_handler:
        for i in range(2):
            await client.send_key(Keycode.F, 0.1)
            await asyncio.sleep(.2)

        if await is_visible_by_path(client, enter_true_friend_code_button_path):
            await click_window_by_path(client, enter_true_friend_code_button_path)

        await asyncio.sleep(.3)

        # *** This does not work ***
        for i in range(len(tfc)):
            # convert characters to keycodes, press each one
            await client.send_key(Keycode.W)
            await asyncio.sleep(.15)

        #if await is_visible_by_path(client, )


async def exit_menus(c: Client, paths):
    for i in paths:
        click_button = await get_window_from_path(c.root_window, i)
        if click_button:
            if await click_button.is_visible():
                async with c.mouse_handler:
                    await c.mouse_handler.click_window(click_button)


async def safe_click_window(client: Client, path):
    if await is_visible_by_path(client, path):
        async with client.mouse_handler:
            await click_window_by_path(client, path)



async def click_window_by_path(client: Client, path: list[str], hooks: bool = False):
    # FULL CREDIT TO SIROLAF FOR THIS FUNCTION, notfaj was here :3
    # clicks window from path, must actually exist in the UI tree
    async with client.mouse_handler:
        root = client.root_window
        windows = await get_window_from_path(root, path)
        if windows:
            await client.mouse_handler.click_window(windows)
        else:
            await asyncio.sleep(0.1)



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


async def wait_for_zone_change(client: Client, current_zone: str = None, to_zone: str = None, loading_only: bool = False):
    # Wait for zone to change, allows for waiting in team up forever without any extra checks
    logger.debug(f'Client {client.title} - Awaiting loading')
    if not loading_only:
        # if to_zone is present, wait until we reach the selected zone
        if to_zone is not None:
            while await client.zone_name() != to_zone:
                await asyncio.sleep(0.1)

        # otherwise wait until our zone changes from whatever it was previously
        else:
            if current_zone is None:
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
    current_zone = await client.zone_name()
    await click_window_by_path(client, spiral_door_teleport_path, True)
    await wait_for_zone_change(client, current_zone=current_zone)


async def navigate_to_ravenwood(client: Client):
    # navigates to commons from anywhere in the game
    current_zone = await client.zone_name()

    await client.send_key(Keycode.HOME, 0.1)
    await client.send_key(Keycode.HOME, 0.1)

    await wait_for_zone_change(client, current_zone=current_zone)
    use_spiral_door = False
    bartleby_navigation = True
    current_zone = await client.zone_name()
    match current_zone:
        # Handling for dorm room
        case "WizardCity/Interiors/WC_Housing_Dorm_Interior":
            await client.goto(70.15016174316406, 9.419374465942383)
            while not await client.is_loading():
                await client.send_key(Keycode.S, 0.1)
            await wait_for_zone_change(client, current_zone=current_zone)
            bartleby_navigation = False

        # Handling for arcanum apartment
        case "Housing_AR_Dormroom/Interior":
            while not await client.is_loading():
                await client.send_key(Keycode.S, 0.1)
            await wait_for_zone_change(client, current_zone=current_zone)
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
        await client.send_key(Keycode.W, 0.3)

        while True:
            try:
                await safe_wait_for_zone_change(client, name='WizardCity/WC_Ravenwood_Teleporter', handle_hooks_if_needed=True)
                break
            # backup since the above method fails sometimes
            except LoadingScreenNotFound:
                await client.teleport(XYZ(x=18.072603225708008, y=-3250.805419921875, z=244.01708984375))
                await client.send_key(Keycode.W, 0.5)


async def navigate_to_commons_from_ravenwood(client: Client):
    # walk to ravenwood exit
    await client.goto(-19.549846649169922, -297.7527160644531)
    await client.goto(-5.701, -1536.491)
    current_zone = await client.zone_name()
    while not await client.is_loading():
        await client.send_key(Keycode.W, 0.1)
    await wait_for_zone_change(client, current_zone=current_zone)


async def navigate_to_potions(client: Client):
    hilda = XYZ(-4398.70654296875, 1016.1954345703125, 229.00079345703125)
     # make sure client is not loading
    while await client.is_loading():
      await asyncio.sleep(0.1)
      #Teleports to Hilda if not already in range
    while not await client.is_in_npc_range():
      await client.teleport(hilda)
      await asyncio.sleep(1)
    # Teleport to hilda brewer


async def buy_potions(client: Client, recall: bool = True, original_zone=None):
    try:
        await asyncio.sleep(1.0)
        max_potions = await client.stats.potion_max()
        # buy potions and close the potions menu, and recall if needed
        for i in range(2):
            original_potion_count = await client.stats.potion_charge()
            current_potion_count = original_potion_count

            # buy potions until our potion count has either increased (we may not have enough gold for all potions) or we are at max potions
            while current_potion_count == original_potion_count and current_potion_count < max_potions:
                while not await is_visible_by_path(client, potion_shop_base_path):
                    await client.send_key(Keycode.X, 0.1)
                await asyncio.sleep(0.5)

                await click_window_by_path(client, potion_fill_all_path, True)
                await asyncio.sleep(0.25)

                await click_window_by_path(client, potion_buy_path, True)
                await asyncio.sleep(0.25)

                while await is_visible_by_path(client, potion_shop_base_path):
                    await click_window_by_path(client, potion_exit_path, True)
                    await asyncio.sleep(0.125)

                current_potion_count = await client.stats.potion_charge()
                await asyncio.sleep(.5)

            if i == 0:
                if await client.stats.potion_charge() >= 1.0:
                    original_potion_count = await client.stats.potion_charge()

                    while await client.stats.potion_charge() == original_potion_count:
                        logger.debug(f'Client {client.title} - Using potion')
                        await click_window_by_path(client, potion_usage_path, True)
                        await asyncio.sleep(3.0)

    except:
        print(traceback.print_exc())
        raise KeyboardInterrupt

# Put an extra check here in case Starrfox becomes a time traveller or someone is using cheat engine at 100x speed, causing this logic to somehow fail
    if recall:
        current_zone = await client.zone_name()

        # only recall if we're actually going to a new zone
        if original_zone != current_zone:
            while True:
                await client.send_key(Keycode.PAGE_UP, 0.1)
                await client.send_key(Keycode.PAGE_UP, 0.1)

                try:
                    await safe_wait_for_zone_change(client, name=current_zone, handle_hooks_if_needed=True)
                    break
                # if we timed out, loop and try again
                except LoadingScreenNotFound:
                    pass



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
        # do not recall from potion buy if we were already in the commons - wait for zone change will fail
        if await client.zone_name() == 'WizardCity/WC_Hub':
            recall = False
        else:
            recall = True
            # mark if needed
            if mark:
                await client.send_key(Keycode.PAGE_DOWN, 0.1)
        # Navigate to ravenwood
        await navigate_to_ravenwood(client)
        # Navigate to commons
        await navigate_to_commons_from_ravenwood(client)
        # Navigate to hilda brewer
        await navigate_to_potions(client)
        # Buy potions
        await buy_potions(client, recall=recall)

        if await is_potion_needed(client, minimum_mana):
            await use_potion(client)

        if mark:
            # Teleport back to dungeon if available
            if await is_visible_by_path(client, dungeon_recall_path):
                await click_window_by_path(client, dungeon_recall_path)
            else:
                # Teleport back to mark
                await client.send_key(Keycode.PAGE_UP, 0.1)


async def is_control_grayed(button):
    return await button.read_value_from_offset(688, "bool")


async def change_equipment_set(client: Client, set_number: int):
    async with client.mouse_handler:
        # Press B until backpack opens
        while not await is_visible_by_path(client, backpack_is_visible_path):
            await client.send_key(Keycode.B, 0.1)

        # Click open equipment page button.  Corrects for failed clicks
        while await is_visible_by_path(client, backpack_title_path):
            while not await is_visible_by_path(client, equipment_set_manager_title_path):
                await client.mouse_handler.click_window_with_name('EquipmentManager')

        # Click specific set
        individual_equipment_set = individual_equipment_set_parent_path.copy()
        individual_equipment_set.append('equippedIcon' + str(set_number))
        for i in range(8):
            await click_window_by_path(client, individual_equipment_set)

        # Click equipment set button.  Corrects for failed clicks
        while await is_visible_by_path(client, backpack_title_path) or await is_visible_by_path(client, equipment_set_manager_title_path):
            await client.send_key(Keycode.B, 0.1)


class FriendBusyOrInstanceClosed(Exception):
    def __init__(self, msg='Friend was busy / has teleports disabled, or you attempted to enter an area that is no longer accessible', *args, **kwargs):
        super().__init__(msg, *args, **kwargs)



class LoadingScreenNotFound(Exception):
    def __init__(self, msg='The client never entered a loading screen and safe_wait_for_zone_change timed out', *args, **kwargs):
        super().__init__(msg, *args, **kwargs)



async def safe_wait_for_zone_change(self: Client, name: Optional[str] = None, *, sleep_time: Optional[float] = 0.5, timeout=10.0, handle_hooks_if_needed=True):
    # you should generally provide a zone name via the parameter to prevent a race condition
    if name is None:
        name = await self.zone_name()

    start_time = time.time()
    client_was_in_loading = False
    while await self.zone_name() == name:
        # check so we know if the client ever actually entered a loading screen
        if await self.is_loading():
            client_was_in_loading = True

        if await is_visible_by_path(self, friend_is_busy_and_dungeon_reset_path):
            async with self.mouse_handler:
                await click_window_by_path(self, friend_is_busy_and_dungeon_reset_path)
    
            raise FriendBusyOrInstanceClosed

        if timeout is not None:
            # X seconds have passed
            if time.time() > start_time + timeout and not client_was_in_loading:
                if await self.is_loading():
                    client_was_in_loading = True
                # if after X seconds we have not entered a loading screen and have not seen a friend is busy popup, we're in the same zone
                else:
                    raise LoadingScreenNotFound

        await asyncio.sleep(sleep_time)


async def click_window_until_closed(client: Client, path):
    if await is_visible_by_path(client, path):
        async with client.mouse_handler:
            while await is_visible_by_path(client, path):
                await click_window_by_path(client, path)
        return True

    else:
        return False


async def refill_potions_if_needed(p: Client):
    if await p.stats.potion_charge() < 1.0 and await p.stats.reference_level() >= 6:
        for i in range(3):
            await p.send_key(Keycode.PAGE_DOWN)

        await refill_potions(p, mark=True, recall=False)

        for i in range(3):
            await p.send_key(Keycode.PAGE_UP)

        await p.wait_for_zone_change(name='WizardCity/WC_Hub')
        await asyncio.sleep(2.0)


async def refill_potions(client: Client, mark: bool = False, recall: bool = True, original_zone=None):
    if await client.stats.reference_level() >= 6:
        # mark if needed
        if mark:
            if await client.zone_name() != 'WizardCity/WC_Hub':
                original_mana = await client.stats.current_mana()
                while await client.stats.current_mana() >= original_mana:
                    logger.debug(f'Client {client.title} - Marking Location')
                    await client.send_key(Keycode.PAGE_DOWN, 0.1)
                    await asyncio.sleep(.75)

        # Navigate to ravenwood
        await navigate_to_ravenwood(client)
        # Navigate to commons from ravenwood
        await navigate_to_commons_from_ravenwood(client)
        # Navigate to hilda brewer
        await navigate_to_potions(client)
        # Buy potions
        await buy_potions(client, recall, original_zone=original_zone)


async def auto_potions(client: Client, mark: bool = False, minimum_mana: int = 16, buy: bool = True):
    if await is_potion_needed(client, minimum_mana):
        await use_potion(client)
    # If we have less than 1 potion left, get potions
    if await client.stats.potion_charge() < 1.0 and buy:
        await refill_potions(client, mark=mark)


async def wait_for_window_by_path(client: Client, path: list[str], hooks: bool = False, click: bool = True):
    while not await is_visible_by_path(client, path):
        await asyncio.sleep(0.1)
    if click or hooks:
        await click_window_by_path(client, path, hooks)


# From peechez's dance game bot
async def maybe_find_window_by_name(parent, name):
    for child in await parent.children():
        if await child.name() == name:
            return child
    return None


# From peechez's dance game bot
async def wait_and_return_window_by_path(parent, *path):
    window = parent
    for name in path:
        while (maybe_window := await maybe_find_window_by_name(window, name)) is None:
            pass
        window = maybe_window
    return window


async def post_keys(client, keys):
    user32_dance = ctypes.windll.user32

    for key in keys:
        user32_dance.PostMessageW(client.window_handle, 0x100, ord(key), 0)
        user32_dance.PostMessageW(client.window_handle, 0x101, ord(key), 0)


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


# quest_number - 0-3
# opens book, selects quest, and then closes book
async def select_quest_from_questbook(client: Client, quest_book_sort: list[str], quest_number: int):

    while not await is_visible_by_path(client, quest_book_sort):
        await client.send_key(Keycode.Q)
        await asyncio.sleep(.5)

    if await is_visible_by_path(client, quest_book_sort):
        await click_window_by_path(client, quest_book_sort)

    await asyncio.sleep(.5)

    quest_number_path = quest_buttons_parent_path[:]
    quest_number_path.append('wndQuestInfo' + str(quest_number))
    quest_number_path.append('questInfoWindow')
    quest_number_path.append('wndQuestInfo')
    quest_number_path.append('txtGoal')
    print(quest_number_path)

    for i in range(5):
        if await is_visible_by_path(client, quest_number_path):
            await click_window_by_path(client, quest_number_path)
        await asyncio.sleep(.1)

    await asyncio.sleep(.5)

    while await is_visible_by_path(client, quest_book_sort):
        await client.send_key(Keycode.Q)
        await asyncio.sleep(.5)


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


async def sync_camera(client: Client, xyz: XYZ = None, yaw: float = None):
    # Teleports the freecam to a specified position, yaw, etc.
    if not xyz:
        xyz = await client.body.position()

    if not yaw:
        yaw = await client.body.yaw()

    xyz.z += 200

    camera = await client.game_client.free_camera_controller()
    await camera.write_position(xyz)
    await camera.write_yaw(yaw)


async def _cycle_friends_list(client, right_button, friends_list, icon, icon_list, name, current_page):

    if name is not None:
        name = name.lower()

    list_text = await friends_list.maybe_text()

    match = None
    idx = 0

    for idx, friend_entry in enumerate(list(_friend_list_entry.finditer(list_text))):
        friend_icon = int(friend_entry.group("icon_index"))
        friend_icon_list = int(friend_entry.group("icon_list"))
        friend_name = (friend_entry.group("name")).lower()

        if icon is not None and icon_list is not None and name:
            if (
                friend_icon == icon
                and friend_icon_list == icon_list
                and friend_name == name
            ):
                match = friend_entry
                break

        elif icon is not None and icon_list is not None:
            if friend_icon == icon and friend_icon_list == icon_list:
                match = friend_entry
                break

        elif name:
            if friend_name == name:
                match = friend_entry
                break

        else:
            raise RuntimeError("Invalid args")

    if match:
        target_page = (idx // 10) + 1

        if target_page != current_page:
            for _ in range(target_page - current_page):
                await client.mouse_handler.click_window(right_button)

    return match, idx


# TODO: add error if friend is busy message pops up
async def teleport_to_friend_from_list(
    client, *, icon_list: int = None, icon_index: int = None, name: str = None
):
    """
    Teleport to a friend from the client's friend list

    Args:
        client: Client to teleport
        icon_list: Icon list the icon is from (1 or 2) or None
        icon_index: Index of the icon or None
        name: Name of the player or None
    """
    if (
        icon_list is None
        and icon_index is not None
        or icon_list is not None
        and icon_index is None
    ):
        raise ValueError("Icon list and icon index must both be defined or not defined")

    if all(i is None for i in (icon_list, icon_index, name)):
        raise ValueError("Must specify icon_list and icon_index or name or all")

    try:
        friends_window = await _maybe_get_named_window(
            client.root_window, "NewFriendsListWindow"
        )
    except ValueError:
        # friend's list isn't open so open it
        friend_button = await _maybe_get_named_window(client.root_window, "btnFriends")
        await client.mouse_handler.click_window(friend_button)

        friends_window = await _maybe_get_named_window(
            client.root_window, "NewFriendsListWindow"
        )
    else:
        if not await friends_window.is_visible():
            # friend's list isn't open so open it
            friend_button = await _maybe_get_named_window(client.root_window, "btnFriends")
            await client.mouse_handler.click_window(friend_button)

    await _cycle_to_online_friends(client, friends_window)

    friends_list_window = await _maybe_get_named_window(friends_window, "listFriends")
    friends_list_text = await friends_list_window.maybe_text()

    # no friends online
    if not friends_list_text:
        raise ValueError("No friends online")

    right_button = await _maybe_get_named_window(friends_window, "btnArrowDown")
    page_number = await _maybe_get_named_window(friends_window, "PageNumber")

    page_number_text = await page_number.maybe_text()

    current_page, _ = map(
        int,
        page_number_text.replace("<center>", "")
        .replace("</center>", "")
        .replace(" ", "")
        .split("/"),
    )

    friend, friend_index = await _cycle_friends_list(
        client,
        right_button,
        friends_list_window,
        icon_index,
        icon_list,
        name,
        current_page,
    )

    if friend is None:
        raise ValueError(
            f"Could not find friend with icon {icon_index} icon list {icon_list} and/or name {name}"
        )

    await _click_on_friend(client, friends_list_window, friend_index)

    character_window = await _maybe_get_named_window(client.root_window, "wndCharacter")
    await _teleport_to_friend(client, character_window)

    # close friends window
    await friends_window.write_flags(WindowFlags(2147483648))


# returns True if all provided friends are in the list, and False if any single friend is not
async def check_for_multiple_friends_in_list(client: Client, friend_names: list[str]):

    async with client.mouse_handler:
        
        # if some form of friend list or friend popup is already open, close it
        # This fails consistently, even when the friends list is actually open.  Detecting whether the friends list is open is also horrifically inconsistent so just brute force it
        for i in range(5):
            try:
                await click_window_by_path(client, close_real_friend_list_button_path)
                await asyncio.sleep(.1)
            except ValueError:
                await asyncio.sleep(.1)

        # try:
        #	friends_window = await _maybe_get_named_window(client.root_window, "NewFriendsListWindow")
        # except:

        friend_button = await _maybe_get_named_window(client.root_window, "btnFriends")
        await client.mouse_handler.click_window(friend_button)
        await asyncio.sleep(.4)
        friends_window = await _maybe_get_named_window(client.root_window, "NewFriendsListWindow")

        await _cycle_to_online_friends(client, friends_window)

        friends_list_window = await _maybe_get_named_window(friends_window, "listFriends")

        right_button = await _maybe_get_named_window(friends_window, "btnArrowDown")
        page_number = await _maybe_get_named_window(friends_window, "PageNumber")

        page_number_text = await page_number.maybe_text()

        current_page, _ = map(
            int,
            page_number_text.replace("<center>", "")
                .replace("</center>", "")
                .replace(" ", "")
                .split("/"),
        )

        for friend_name in friend_names:
            friend, friend_index = await _cycle_friends_list(
                client,
                right_button,
                friends_list_window,
                None,
                None,
                friend_name,
                current_page,
            )

            if friend is None:
                return False

        # Pray that we don't mis-press, because we cannot detect the friends list and cannot accurately click it
        for i in range(2):
            await client.send_key(Keycode.F, 0.1)

        # This fails consistently, even when the friends list is actually open.  Detecting whether the friends list is open is also horrifically inconsistent so just brute force it
        for i in range(3):
            try:
                await click_window_by_path(client, close_real_friend_list_button_path)
                await asyncio.sleep(.1)
            except ValueError:
                await asyncio.sleep(.1)

    return True


async def check_for_friend_in_list(client: Client, friend_name: str):
    async with client.mouse_handler:
        # if some form of friend list or friend popup is already open, close it
        # This fails consistently, even when the friends list is actually open.  Detecting whether the friends list is open is also horrifically inconsistent so just brute force it
        for i in range(5):
            try:
                await click_window_by_path(client, close_real_friend_list_button_path)
                await asyncio.sleep(.1)
            except ValueError:
                await asyncio.sleep(.1)

        # try:
        #	friends_window = await _maybe_get_named_window(client.root_window, "NewFriendsListWindow")
        # except:

        friend_button = await _maybe_get_named_window(client.root_window, "btnFriends")
        await client.mouse_handler.click_window(friend_button)
        await asyncio.sleep(.4)
        friends_window = await _maybe_get_named_window(client.root_window, "NewFriendsListWindow")

        await _cycle_to_online_friends(client, friends_window)

        friends_list_window = await _maybe_get_named_window(friends_window, "listFriends")

        right_button = await _maybe_get_named_window(friends_window, "btnArrowDown")
        page_number = await _maybe_get_named_window(friends_window, "PageNumber")

        page_number_text = await page_number.maybe_text()

        current_page, _ = map(
            int,
            page_number_text.replace("<center>", "")
                .replace("</center>", "")
                .replace(" ", "")
                .split("/"),
        )

        friend, friend_index = await _cycle_friends_list(
            client,
            right_button,
            friends_list_window,
            None,
            None,
            friend_name,
            current_page,
        )

        # Pray that we don't mis-press, because we cannot detect the friends list and cannot accurately click it
        for i in range(2):
            await client.send_key(Keycode.F, 0.1)

        # This fails consistently, even when the friends list is actually open.  Detecting whether the friends list is open is also horrifically inconsistent so just brute force it
        for i in range(3):
            try:
                await click_window_by_path(client, close_real_friend_list_button_path)
                await asyncio.sleep(.1)
            except ValueError:
                await asyncio.sleep(.1)

    if friend is None:
        return False
    else:
        return True

# requires that the character screen is already open
async def set_wizard_name_from_character_screen(client: Client):
    option_window = await client.root_window.get_windows_with_name('TitleScroll')
    assert len(option_window) == 1, str(option_window)

    # for child in await option_window[0].children():
    children = await option_window[0].children()
    wizard_name = await children[0].maybe_text()
    wizard_name = wizard_name[8:-9]

    client.wizard_name = wizard_name

# requires that the character screen is already open
async def return_wizard_energy_from_character_screen(client: Client):
    energy_txt_window = await get_window_from_path(client.root_window, energy_amount_path)

    energy_txt = await energy_txt_window.maybe_text()
    current_energy = energy_txt[8:]
    total_energy = energy_txt[8:]
    current_energy = current_energy.split('/', 1)[0]
    total_energy = total_energy.split('/', 1)[1]
    current_energy = int(current_energy)
    total_energy = int(total_energy)

    return current_energy, total_energy


async def get_friend_popup_wizard_name(client: Client):
    option_window = await client.root_window.get_windows_with_name("lblCharacterName")

    if len(option_window) > 0:
        try:
            assert len(option_window) == 1, str(option_window)
        except:
            await asyncio.sleep(.1)

        wizard_name = await option_window[0].maybe_text()
        wizard_name = wizard_name[8:-9]

        return wizard_name
    else:
        return ''


async def collect_wisps(client: Client, nothing_but_safe_entities=True):
    # Collects all the wisps in the current area, only works within the entity draw distance.
    entities = []
    entities = await SprintyClient(client).get_base_entities_with_vague_name('WispHealth')
    entities += await SprintyClient(client).get_base_entities_with_vague_name('WispMana')
    entities += await SprintyClient(client).get_base_entities_with_vague_name('WispGold')

    if nothing_but_safe_entities:
        safe_entities = await SprintyClient(client).find_safe_entities_from(entities)
    else:
        safe_entities = entities

    if safe_entities:
        for entity in safe_entities:
            wisp_xyz = await entity.location()
            await client.teleport(wisp_xyz)
            await asyncio.sleep(0.1)


async def collect_wisps_with_limit(client: Client, limit=3):
    # Collects all the wisps in the current area, only works within the entity draw distance.
    entities = []
    entities = await SprintyClient(client).get_base_entities_with_vague_name('WispHealth')
    entities += await SprintyClient(client).get_base_entities_with_vague_name('WispMana')

    total_collected = 0

    for entity in entities:
        wisp_xyz = await entity.location()
        await client.teleport(wisp_xyz)
        total_collected += 1

        if total_collected == limit:
            break

        await asyncio.sleep(0.1)


async def pid_to_client(clients: List[Client], pid: int) -> Client:
    for client in clients:
        if client.process_id == pid:
            return client

    if clients:
        return clients[0]
    else:
        return None


async def wait_for_visible_by_path(client: Client, path: List[str], wait_for_not: bool = False, interval: float = 0.25):
    if wait_for_not:
        while await is_visible_by_path(client, path):
            await asyncio.sleep(interval)

    else:
        while not await is_visible_by_path(client, path):
            await asyncio.sleep(interval)


async def try_task_coro(coro: Coroutine, clients: List[Client], deactive_mouseless: bool = False):
    task_coro = coro
    try:
        await task_coro()

    except asyncio.CancelledError:
        for p in clients:
            p.feeding_pet_status = False
        await asyncio.gather(*[attempt_deactivate_dance_hook(p) for p in clients])
        pass

    except wizwalker.errors.MemoryInvalidated | wizwalker.errors.ExceptionalTimeout:
        await try_task_coro(coro, clients, deactive_mouseless)

    finally:
        pass


def index_with_str(input_str, desired_str: str) -> int:
    for i, s in enumerate(input_str):
        if desired_str in s.lower():
            return i

    return None


def read_webpage(url):
    # return a list of lines from a hosted file
    try:
        response = requests.get(url, allow_redirects=True)
        page_text = response.text
        line_list = page_text.splitlines()

    except:
        return []

    else:
        return line_list


def assign_pet_level(destinationLevel):
    pet_world_tracks = ['btnTrack0', 'btnTrack1', 'btnTrack2', 'btnTrack3', 'btnTrack4']
    pet_world_list = ['WizardCity', 'Krokotopia', 'Marleybone', 'Mooshu', 'Dragonspyre']

    pet_world_index = pet_world_list.index(destinationLevel)
    selected_track = pet_world_tracks[pet_world_index]

    if selected_track is not None:
        for index, track in enumerate(wizard_city_dance_game_path):
            if (track in pet_world_tracks):
                wizard_city_dance_game_path[index] = selected_track


def required_params(signature: inspect.Signature) -> int:
    '''Counts the number of params required for a function, based off of its function signature.'''
    req_params = 0

    for param in signature.parameters.values():
        if param.default is inspect.Parameter.empty:
            req_params += 1

    return req_params


async def conditional_await(func, args: dict = {}) -> Any:
    '''Awaits any function that returns something if async, runs normally if sync.'''
    if inspect.iscoroutinefunction(func):
        return await func(**args)

    else:
        return func(**args)



async def class_snapshot(instance, recurse: bool = True, current_depth: int = 0, max_depth: int = 25, types_blacklist = (inspect._empty, Window, wizwalker.memory.DynamicWindow), edge_cases: dict = {}):
    '''Recursively calls every function in a class, async or not. Assembles a dict containing the outputs for these, referenced by function name. Only does functions that have no arguments.'''
    snapshot_data = {}

    if current_depth >= max_depth: #If we have reached or exceeded max depth, return an empty dict
        return snapshot_data
    
    if not recurse and current_depth: #If we have any depth and we are not recursing, return an empty dict
        return snapshot_data

    current_depth += 1 #Tick our current depth

    valid_types = (int, float, bool, str, Enum, type(None)) #valid built-in types
    iter_types = (list, dict, set, tuple) #types we can iterate through in a useful manner, as strings are iterable

    def _is_valid_type(obj, types = valid_types):
        #Returns True if the object supplied's type is apart of the list of supplied valid types
        return issubclass(type(obj), types)

    def _is_return_type_blacklisted(func, types: tuple = types_blacklist):
        return_type = typing.get_type_hints(func).get("return")
        if isinstance(return_type, typing._GenericAlias):
            return_type = return_type.__args__[0]

        return issubclass(return_type, types)

    for name, func in inspect.getmembers(instance, predicate=inspect.ismethod):
        signature = inspect.signature(func)
        if name in edge_cases:
            edge_case_args = edge_cases[name]
            is_func_compat = True

        else:
            edge_case_args = {}
            is_func_compat = (not name.startswith('__') and not len(signature.parameters) and not _is_return_type_blacklisted(func))

        if is_func_compat: # Skip built-in methods and only consider functions without arguments
            try:
                output = await conditional_await(func, edge_case_args)

            except Exception as e: #This is sussy, but some functions will inevitably error and we want to continue regardless. - slack
                snapshot_data[name] = None
                continue

            if issubclass(type(output), Enum): #Use only the value of the enum
                output = output.value

            if _is_valid_type(output): #If this is just normal data, we can use the output
                snapshot_data[name] = output

            elif _is_valid_type(output, iter_types): #If the output is iterable, check everything inside it
                if issubclass(type(output), dict): #dict handling, checks both the keys and values
                    output_dict = {}
                    for o_k, o_v in output:
                        snapshot_k = o_k
                        snapshot_v = o_v

                        if not _is_valid_type(o_k): #If this isn't a built-in type, we know it has inner complexity so we recurse
                            snapshot_k = await class_snapshot(o_k, recurse, current_depth, max_depth, types_blacklist, edge_cases)

                        if not _is_valid_type(o_v):
                            snapshot_v = await class_snapshot(o_v, recurse, current_depth, max_depth, types_blacklist, edge_cases)

                        output_dict[snapshot_k] = snapshot_v

                    snapshot_data[name] = output_dict
                    continue

                else:
                    output_iterable = [] #Iterable output handling, checks the types inside the iterable
                    for o in output:
                        if _is_valid_type(o):
                            output_iterable.append(o)
                            continue

                        o_snapshot = await class_snapshot(o, recurse, current_depth, max_depth, types_blacklist, edge_cases)
                        output_iterable.append(o_snapshot)

                snapshot_data[name] = type(output)(output_iterable) #Mirror the output type of the iterable so it's preserved in the snapshot

            else:
                snapshot_data[name] = await class_snapshot(output, recurse, current_depth, max_depth, types_blacklist, edge_cases)

    return snapshot_data


async def class_snapshot_iterable(instances: Iterable, recurse: bool = True, current_depth: int = 0, max_depth: int = 25, types_blacklist = (inspect._empty, Window, wizwalker.memory.DynamicWindow), edge_cases: dict = {}):
    snapshots = []
    for inst in instances:
        snapshots.append(await class_snapshot(inst, recurse, current_depth, max_depth, types_blacklist, edge_cases))

    return snapshots


def override_wiz_install_using_handle(max_size = 100):
    """
    This function allows you to automatically override your wiz install location, provided that wizard101 is open.
    """
    path = ctypes.create_unicode_buffer(max_size)
    pid = get_pid_from_handle(get_all_wizard_handles()[0])
    handle = kernel32.OpenProcess(0x410, 0, pid) # PROCESS_QUERY_INFORMATION and PROCESS_VM_READ
    ctypes.windll.psapi.GetModuleFileNameExW(handle, None, ctypes.byref(path), max_size)
    kernel32.CloseHandle(handle)
    install_location = path.value.replace("\Bin\WizardGraphicalClient.exe", "")
    override_wiz_install_location(install_location)
