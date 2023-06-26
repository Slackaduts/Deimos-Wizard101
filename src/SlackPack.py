import asyncio
import time

import wizwalker
from wizwalker import Keycode, HotkeyListener, ModifierKeys, utils
# from wizwalker import WizWalker
from wizwalker.client_handler import ClientHandler
from wizwalker.memory import Window
from src.utils import *
from src.paths import *
import re
from loguru import logger

try:
    from wizwalker.memory import MagicSchool
except ImportError:
    from enum import Enum
    # In case enum isn't imported, we import it
    # Below Magic School class is for determining what class the user is for calculating
    # Example: If we have an item that is equippable that has Death Damage for our Life Wizard we want to skip that value
    class MagicSchool(Enum):
        ice = 72777
        sun = 78483
        life = 2330892
        fire = 2343174
        star = 2625203
        myth = 2448141
        moon = 2504141
        death = 78318724
        storm = 83375795
        gardening = 663550619
        castle_magic = 806477568
        whirly_burly = 931528087
        balance = 1027491821
        shadow = 1429009101
        fishing = 1488274711
        cantrips = 1760873841


class SlackPackError(Exception):
    """SlackPack Error"""


# @logger.catch
class SlackPack:
    def __init__(self, client) -> None:
        self.client = client
        self.root_window = client.root_window
        self.mouse_handler = client.mouse_handler
        self.schools = [
            'life',
            'fire',
            'myth',
            'ice',
            'death',
            'balance',
            'storm',
        ]
        self.tabs = [
            "Tab_Hat",
            "Tab_Robe",
            "Tab_Shoes",
            "Tab_Weapon",
            "Tab_Athame",
            "Tab_Amulet",
            "Tab_Ring"
        ]
        self.clients_school = None

        self.neat_damage = 0
        self.neat_maxhealth = 0
        self.neat_accuracy = 0
        self.neat_resist = 0
        self.neat_criticalrating = 0
        self.neat_piercing = 0
        self.neat_pips = 0


        self.current_equipped_item = 0
        self.current_new_item = 0

    async def open_and_parse_backpack_contents(self, client):
        # Opens backpack, parses through backpack tabs, does not parse items, different function
        async with client.mouse_handler:
            while not await get_window_from_path(self.root_window, ["WorldView", "DeckConfiguration", "InventorySpellbookPage"]):
                await self.client.send_key(Keycode.B, 0.1)
                # Wait for backpack to be open
            left_button = await get_window_from_path(self.root_window, ['WorldView', 'DeckConfiguration', 'InventorySpellbookPage', 'leftscroll'])
            right_button = await get_window_from_path(self.root_window, ['WorldView', 'DeckConfiguration', 'InventorySpellbookPage', 'rightscroll'])
            # Sets left and right buttons for multiple pages
            for tab in self.tabs:
                # Defined list of tabs to search through for better items
                self.current_equipped_item = 0
                await self.client.mouse_handler.click_window_with_name(tab)
                if await left_button.is_visible():
                    while not await is_control_grayed(left_button):
                        # Sometimes remembers users page, so we detect if user is on a page other than page 1
                        await self.mouse_handler.click_window(left_button)
                    while not await is_control_grayed(right_button):
                        if await self.scan() is not None:
                            pass
                        await self.mouse_handler.click_window(right_button)
                    # Above is logic to check for multiple pages
                if await self.scan() is not None:
                    # Logic for one page
                    pass
            while await get_window_from_path(self.root_window, ["WorldView", "DeckConfiguration", "InventorySpellbookPage"]):
                await self.client.send_key(Keycode.B, 0.1)
                # await asyncio.sleep(.2)

    async def scan(self):
        for instance in await self.client.client_object.inactive_behaviors():
            # Reads clients Magic School for reading item stats
            if await instance.read_type_name() == "ClientMagicSchoolBehavior":
                # make this a memory object
                address = await instance.read_base_address()
                school_id = await self.client.hook_handler.read_typed(address + 128, "unsigned int")
                school = str(MagicSchool(school_id))
                parse_school = school.split('.')
                self.clients_school = parse_school[1]

        for i in range(1, 9):
            # Find each item on the page
            hovered_item = await get_window_from_path(self.root_window, ["WorldView", "DeckConfiguration", f"InventorySpellbookPage", f"Item_{i}"])
            item_is_not_equippable = await is_control_grayed(hovered_item)
            if item_is_not_equippable:
                # If item is not the class type of the user, skip it
                continue
            await self.mouse_handler.set_mouse_position_to_window(hovered_item)
            await asyncio.sleep(.05)
            if await is_visible_by_path(self.client, equipped_item):
                # Calculates if
                await self.calculate(i)
            else:
                await self.mouse_handler.click_window_with_name(f"Item_{i}")
                await self.mouse_handler.click_window_with_name("Equip_Item")
                await asyncio.sleep(1)

    async def calculate(self, i):
        # This function needs to calculate an item that is NOT equipped. We hover over the item to check if
        # equipped_item and new_item Window is visible. If they are both visible we go into this function to calculate.
        # We need to store the equipped item stat each time we hover over a new item because the equipped item could
        # change.
        equippedItemPath = await get_window_from_path(self.root_window, equipped_item)
        newItemPath = await get_window_from_path(self.root_window, new_item)
        under_20 = await self.client.stats.reference_level()
        stats = []
        self.current_new_item = 0
        self.neat_damage = 0
        self.neat_maxhealth = 0
        self.neat_accuracy = 0
        self.neat_resist = 0
        self.neat_criticalrating = 0
        self.neat_piercing = 0
        self.neat_pips = 0
        # Resetting each value during each calculation so no values stick overtime

        if not newItemPath:
            stats = await equippedItemPath.children()
        elif newItemPath:
            stats = await newItemPath.children()
        # Setting the path for the item and getting the stats from each line inside the Window

        for stat in stats:
            # Read each value in stats: Contains, Name, Link to image.jpg, and Stat, and we only want the
            stat_text_lower = (await stat.maybe_text()).lower()
            if "damage" in stat_text_lower:
                if self.clients_school in stat_text_lower:
                    await self.clean_up_stat(stat_text_lower, "damage", "neat_damage", i)
            if "maxhealth" in stat_text_lower:
                await self.clean_up_stat(stat_text_lower, "maxhealth", "neat_maxhealth", i)
            if "accuracy" in stat_text_lower:
                await self.clean_up_stat(stat_text_lower, "accuracy", "neat_accuracy", i)
            if "resist" in stat_text_lower:
                for x in self.schools:
                    if x in stat_text_lower:
                        # We want universal resist in our calculation not school resist
                        break
                    else:
                        await self.clean_up_stat(stat_text_lower, "resist", "neat_resist", i)
            if "criticalrating" in stat_text_lower:
                await self.clean_up_stat(stat_text_lower, "criticalrating", "neat_criticalrating", i)
            if "piercing" in stat_text_lower:
                await self.clean_up_stat(stat_text_lower, "piercing", "neat_piercing", i)
            if "pips" in stat_text_lower:
                await self.clean_up_stat(stat_text_lower, "pips", "neat_pips", i)
        if under_20 <= 20:
            # Checks if player is under lvl 20. If so we value health over anything so the user can live early on
            self.current_new_item = (int(self.neat_damage) + int(self.neat_maxhealth) + int(self.neat_accuracy) + int(self.neat_resist) + int(self.neat_criticalrating) + int(self.neat_piercing) + int(self.neat_pips))
        else:
            # If player is not under lvl 20, we lower healths weighted value
            self.current_new_item = (int(self.neat_damage) + (int(self.neat_maxhealth) / 100) + int(self.neat_accuracy) + int(self.neat_resist) + int(self.neat_criticalrating) + int(self.neat_piercing) + int(self.neat_pips))

        await asyncio.sleep(.1)
        if self.current_new_item > self.current_equipped_item:
            # Logic for equipping a better item
            if i == 1:
                self.current_equipped_item = self.current_new_item
                # Don't click equip on current equipped item. It will cause it to unequip
                return
            else:
                self.current_equipped_item = self.current_new_item
                await self.mouse_handler.click_window_with_name(f"Item_{i}")
                await self.mouse_handler.click_window_with_name("Equip_Item")
                await asyncio.sleep(1)
        # Each var for current_new_item needs reset (accuracy, health, etc)
        # TODO - Make function to reset all variables when switching to next item

    async def clean_up_stat(self, stat_text_lower, keyword, attribute_name, i):
        # Removes information we don't need from stat
        cluttered_stat = stat_text_lower
        plus_position = cluttered_stat.find('+')
        end_position = cluttered_stat.find(' <image')
        neat_stat = cluttered_stat[plus_position + 1:end_position]
        cleaned_stat = re.sub("[^0-9]", "", neat_stat)
        setattr(self, attribute_name, cleaned_stat)
        # print(i, attribute_name.capitalize() + ':', getattr(self, attribute_name), '\n')

    async def main(self, client):
        await self.open_and_parse_backpack_contents(client)

