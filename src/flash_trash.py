import asyncio
import re
from wizwalker.memory.memory_reader import MemoryReadError
from wizwalker.extensions.scripting.utils import _maybe_get_named_window
from src.utils import *
from loguru import logger


# TODO - We need to check if the trying to get a window fails, if it fails we break from the sell action
class FlashTrash:
    def __init__(self, client: "Client"):
        self.client = client
        self.spell_book_is_open = None
        self.inventory_page = None
        self.equippble_tab = ['ShopCategory_Hat',
                     'ShopCategory_Robe',
                     'ShopCategory_Shoes',
                     'ShopCategory_Weapon',
                     'ShopCategory_Athame',
                     'ShopCategory_Amulet',
                     'ShopCategory_Ring',
                     'ShopCategory_Deck']
        self.housing_tab = ['ShopCategory_CastleBlock',
                            'ShopCategory_PlantLife',
                            'ShopCategory_WallHangings',
                            'ShopCategory_WallpaperCarpet',
                            'ShopCategory_Outdoor',
                            'ShopCategory_Furniture',
                            'ShopCategory_Decoration',
                            'ShopCategory_MusicScroll',
                            'ShopCategory_Seed']

    async def open(self):
        pass

    async def close(self):
        pass

    async def __aenter__(self):
        await self.open()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def _check_if_window_is_visible(self, window: str):
        try:
            self.window = await _maybe_get_named_window(self.client.root_window, window)
        except ValueError:
            self.window = None
        return self.window

    async def check_if_client_is_close_to_max_gold(self) -> bool:
        if not await self._check_if_window_is_visible('DeckConfiguration'):
            # print('Spell book not open, manually opening spellbook')
            spellbook = await _maybe_get_named_window(self.client.root_window, "btnSpellbook")
            async with self.client.mouse_handler:
                await self.client.mouse_handler.click_window(spellbook)
            await asyncio.sleep(.2)
        select_character_stats_for_max_gold_calculation = await _maybe_get_named_window(self.client.root_window, 'CharStats')
        async with self.client.mouse_handler:
            await self.client.mouse_handler.click_window(select_character_stats_for_max_gold_calculation)

        window_of_client_current_gold = await _maybe_get_named_window(self.client.root_window, 'Gold')
        messy_client_current_gold = await window_of_client_current_gold.read_wide_string_from_offset(584)
        string_client_current_gold = re.sub('\D', '', messy_client_current_gold)
        client_current_gold = int(string_client_current_gold)


        window_of_client_max_gold = await _maybe_get_named_window(self.client.root_window, 'GoldMax')
        messy_client_max_gold = await window_of_client_max_gold.read_wide_string_from_offset(584)
        string_client_max_gold = re.sub('\D', '', messy_client_max_gold)
        client_max_gold = int(string_client_max_gold)
        client_max_gold_safe_zone = client_max_gold - 20000

        if client_max_gold_safe_zone < client_current_gold:
            logger.debug(f'Client {self.client.title} - is too close to max gold to sell items \nCurrent Gold: {client_current_gold} \nMax Gold: {client_max_gold_safe_zone + 20000} ')
            return True
        else:
            return False

    async def check_if_client_is_close_to_max_backpack_space(self) -> bool:
        spell_book_is_open = await self._check_if_window_is_visible('DeckConfiguration')

        # If spell book is not open, it returns none. We go into the "none if statement" and open the spellbook
        if not spell_book_is_open:
            # print('Spell book not open, manually opening spellbook')
            spellbook = await _maybe_get_named_window(self.client.root_window, "btnSpellbook")
            async with self.client.mouse_handler:
                await self.client.mouse_handler.click_window(spellbook)
            await asyncio.sleep(.2)

        inventory_page = await self._check_if_window_is_visible('InventorySpellbookPage')
        # If current page isn't inventory page it returns none. We go into the none if-statement and open the inventory
        if not inventory_page:
            # print('Current page is not backpack, switch to backpack page')
            select_inventory_tab = await _maybe_get_named_window(self.client.root_window, "Inventory")
            async with self.client.mouse_handler:
                await self.client.mouse_handler.click_window(select_inventory_tab)
            await asyncio.sleep(.5)

        back_pack_space = await _maybe_get_named_window(self.client.root_window, 'inventorySpace')
        messy_back_pack_space = await back_pack_space.read_wide_string_from_offset(584)
        messy_back_pack_space2 = messy_back_pack_space.replace('<center>', '')
        split_back_pack_space = messy_back_pack_space2.split('/')
        back_pack_max_string, back_pack_current_string = split_back_pack_space[1], split_back_pack_space[0]
        back_pack_max, back_pack_current = int(back_pack_max_string), int(back_pack_current_string)

        if spell_book_is_open:
            # print('Spell book not open, manually opening spellbook')
            spellbook = await _maybe_get_named_window(self.client.root_window, "btnSpellbook")
            async with self.client.mouse_handler:
                await self.client.mouse_handler.click_window(spellbook)
            await asyncio.sleep(.2)

        if back_pack_current > back_pack_max - 10:
            return True
        else:
            return False

    async def open_quick_sell_menu(self) -> None:
        # General Logic for detecting if spell book is open, if it's open we need to make sure its on the right tab
        # To Keep it simple, we are starting on Backpack tab, moving to Housing, and Finally Jewels (for now at least)

        spell_book_is_open = await self._check_if_window_is_visible('DeckConfiguration')

        # If spell book is not open, it returns none. We go into the "none if statement" and open the spellbook
        if not spell_book_is_open:
            # print('Spell book not open, manually opening spellbook')
            spellbook = await _maybe_get_named_window(self.client.root_window, "btnSpellbook")
            async with self.client.mouse_handler:
                await self.client.mouse_handler.click_window(spellbook)
            await asyncio.sleep(.2)

        if await self.check_if_client_is_close_to_max_gold():
            # We are checking if gold is close to max. If it is, we close the spell book to allow sigil to continue
            spellbook = await _maybe_get_named_window(self.client.root_window, "btnSpellbook")
            async with self.client.mouse_handler:
                await self.client.mouse_handler.click_window(spellbook)
            return

        inventory_page = await self._check_if_window_is_visible('InventorySpellbookPage')
        # If current page isn't inventory page it returns none. We go into the none if-statement and open the inventory
        if not inventory_page:
            # print('Current page is not backpack, switch to backpack page')
            select_inventory_tab = await _maybe_get_named_window(self.client.root_window, "Inventory")
            async with self.client.mouse_handler:
                await self.client.mouse_handler.click_window(select_inventory_tab)
            await asyncio.sleep(.5)

        # Sometimes the spellbook opening takes some time, so we try and get it, if it fails we just wait and try again
        try:
            quick_sell_tab = await _maybe_get_named_window(self.client.root_window, "QuickSell_Item")
        except ValueError:
            await asyncio.sleep(2)
            quick_sell_tab = await _maybe_get_named_window(self.client.root_window, "QuickSell_Item")

        # I don't know how to detect if the user is on the All Equipments Tab, so we just click it no matter what
        async with self.client.mouse_handler:
            await self.client.mouse_handler.click_window(quick_sell_tab)
        await asyncio.sleep(1)

        select_all_tab = await _maybe_get_named_window(self.client.root_window, 'ShopCategory_All')

        async with self.client.mouse_handler:
            await self.client.mouse_handler.click_window(select_all_tab)
        await asyncio.sleep(.2)

    async def read_each_item(self):
        for i in range(0, 10):
            # We set the path for 'i' which is the item we want to check if we can sell it
            try:
                item = await get_window_from_path(self.client.root_window, ["WorldView", "shopGUI", "buyWindow", "column0", f"shoplist{i}"])
                messy_item_name = await item.read_wide_string_from_offset(616)
                lower_item_name_illegal_characters = messy_item_name.lower()
                item_name = re.sub('[^A-Za-z0-9 ]+', '', lower_item_name_illegal_characters)
            except MemoryReadError:
                # If there is no item to sell, we dont care to read each item.
                pass

            # Convert String to list of items to sell
            file_of_items_to_sell = open('items_to_sell.txt', 'r')
            string_of_items_to_sell = file_of_items_to_sell.read()
            list_of_items_to_sell = string_of_items_to_sell.split(",")

            if item_name in list_of_items_to_sell and item_name != '':
                item_to_sell_check_box = await get_window_from_path(self.client.root_window, ["WorldView", "shopGUI", "buyWindow", "column1", f"num{i}"])
                check_box_rectangle = await item_to_sell_check_box.scale_to_client()
                async with self.client.mouse_handler:
                    await self.client.mouse_handler.click(*(check_box_rectangle.center()))
                    logger.debug(f'Client {self.client.title} - Quick Selling {item_name}')

    async def logic_for_finalizing_sale(self) -> None:
        quick_sell_items = await _maybe_get_named_window(self.client.root_window, 'sellAction')
        if not await is_control_grayed(quick_sell_items):
            async with self.client.mouse_handler:
                await self.client.mouse_handler.click_window(quick_sell_items)

            confirm_quick_sell_items = await _maybe_get_named_window(self.client.root_window, 'SellButton')
            async with self.client.mouse_handler:
                await self.client.mouse_handler.click_window(confirm_quick_sell_items)

            if await self._check_if_window_is_visible('leftButton'):
                confirm_quick_sell_crowns_item = await _maybe_get_named_window(self.client.root_window,'leftButton')
                async with self.client.mouse_handler:
                    await self.client.mouse_handler.click_window(confirm_quick_sell_crowns_item)

            if await self._check_if_window_is_visible('leftButton'):
                # We go again incase user is trying to quick sell a pet. We allow the user to sell pets
                # because bosses/dungeons drop pets
                confirm_quick_sell_crowns_item = await _maybe_get_named_window(self.client.root_window,'leftButton')
                async with self.client.mouse_handler:
                    await self.client.mouse_handler.click_window(confirm_quick_sell_crowns_item)

            please_wait = await get_window_from_path(self.client.root_window, ['WorldView', 'shopGUI', 'QuickSellWaitingWindow'])
            try:
                while await please_wait.is_visible():
                    try:
                        please_wait = await _maybe_get_named_window(self.client.root_window, 'QuickSellWaitingWindow')
                    except ValueError:
                        break
            except AttributeError:
                logger.debug(f'Client {self.client.title} - Could not find "please_wait" window, likely too quick?')
        else:
            close_shop = await _maybe_get_named_window(self.client.root_window, 'exit')
            async with self.client.mouse_handler:
                await self.client.mouse_handler.click_window(close_shop)
            await asyncio.sleep(.2)

        await asyncio.sleep(1)
        close_back_pack = await _maybe_get_named_window(self.client.root_window, 'Close_Button')
        async with self.client.mouse_handler:
            await self.client.mouse_handler.click_window(close_back_pack)
        await asyncio.sleep(.2)

    @logger.catch()
    async def open_and_select_backpack_all_tab(self) -> None:
        # Logic for opening backpack to Quick Sell Menu
        try:
            if not await self.check_if_client_is_close_to_max_gold():
                await self.open_quick_sell_menu()
                # Check what page the user is on. If they aren't on the first page, set them to the first page

                left_button = await _maybe_get_named_window(self.client.root_window, 'leftscroll')
                right_button = await _maybe_get_named_window(self.client.root_window, 'rightscroll')
                if await left_button.is_visible():
                    while not await is_control_grayed(left_button):
                        async with self.client.mouse_handler:
                            await asyncio.sleep(.2)
                            await self.client.mouse_handler.click_window(left_button)
                while not await is_control_grayed(right_button):
                    async with self.client.mouse_handler:
                        await asyncio.sleep(.2)
                        await self.read_each_item()
                        await self.client.mouse_handler.click_window(right_button)
                # Below reads final page contents
                await self.read_each_item()
                await asyncio.sleep(.2)

                # Logic for finalizing sale + returning character to neutral state so other tools don't break
                await self.logic_for_finalizing_sale()
            else:
                logger.debug(f'Client {self.client.title} - is close to max gold, farming continues but no auto sell')
                async with self.client.mouse_handler:
                    await self.client.mouse_handler.click_window_with_name('Close_Button')
        except ValueError:
            # For what ever reason, Wizard101  allows you to open the spellbook, then open the quick sell, THEN
            # Again open a new spell_book. UI Tree doesn't register the spellbook behind the quick sell menu
            # So it messes it up.
            # This exception normally runs when it tries to get the left_button, because UI Tree see's 2or3 left buttons
            # So in case the script opens all 3 windows, we do this to just skip this cycle of quick sell
            # Also this error rarely occurs and happens maybe once every 7 hours, hard to debug when it happens, so we
            # just do this to fix the issue instead of actually fixing the issue
            async with self.client.mouse_handler:
                await self.client.mouse_handler.click_window_with_name('Close_Button')
            async with self.client.mouse_handler:
                await self.client.mouse_handler.click_window_with_name('exit')
            async with self.client.mouse_handler:
                await self.client.mouse_handler.click_window_with_name('Close_Button')

    async def goto_bazzar_and_open_sell_tab(self) -> None:
        await self.client.send_key(Keycode.PAGE_DOWN)
        await navigate_to_ravenwood(self.client)
        await navigate_to_commons_from_ravenwood(self.client)
        await navigate_to_shopping_district(self.client)
        await navigate_to_olde_town(self.client)
        await navigate_to_bazzar(self.client)
        await self.client.send_key(Keycode.PAGE_DOWN)

    async def navigate_to_sell_tab(self) -> None:
        await asyncio.sleep(1)
        async with self.client.mouse_handler:
            await self.client.mouse_handler.click_window_with_name('sellTab')

    async def read_each_shop_item(self, tab):
        tab_window = await _maybe_get_named_window(self.client.root_window, tab)
        if await tab_window.read_value_from_offset(688, 'bool') is True:
            return
        async with self.client.mouse_handler:
            await self.client.mouse_handler.click_window_with_name(tab)
        for i in range(0, 7):
            try:
                # We set the path for 'i' which is the item we want to check if we can sell it
                item_path = ["WorldView", "shopGUI", "sellWindow", f"shoplist{i}"]
                item = await get_window_from_path(self.client.root_window, item_path)
                messy_item_name = await item.read_wide_string_from_offset(616)
                lower_item_name_illegal_characters = messy_item_name.lower()
                item_name = re.sub('[^A-Za-z0-9 ]+', '', lower_item_name_illegal_characters)
                # Below logic is cancer, but I don't see a problem with it. It checks if items can be sold,
                # If item is sold it re-gets the index of the item sold because selling the item removes it from your
                # sellable inventory and puts a new item in that slot, we check if THAT item is
            except MemoryReadError:
                pass

            # Convert String to list of items to sell
            file_of_items_to_sell = open('items_to_sell.txt', 'r')
            string_of_items_to_sell = file_of_items_to_sell.read()
            list_of_items_to_sell = string_of_items_to_sell.split(",")

            if item_name in list_of_items_to_sell:
                # If item is in list of items to sell, enter this code
                await click_window_by_path(self.client, path=item_path)
                sell_button = await _maybe_get_named_window(self.client.root_window, 'sellAction')
                # Above logic is for the first item that is sellable, once we sell an item it is 'popped'
                # out of the stack but we dont update the list of items below this item. If we continued
                # with the logic whe have we'd sell every other item because the stack shrinks and replaces
                # the void of the sold item with a new item.
                if await sell_button.read_value_from_offset(688, 'bool') is True:
                    # Since the void is replaced with a new item we are checking if the next item in the list is
                    # sellable, if not go to next item.
                    continue
                else:
                    while await sell_button.read_value_from_offset(688, 'bool') is False:
                        await asyncio.sleep(1)
                        item = await get_window_from_path(self.client.root_window, item_path)
                        messy_item_name = await item.read_wide_string_from_offset(616)
                        lower_item_name_illegal_characters = messy_item_name.lower()
                        item_name = re.sub('[^A-Za-z0-9 ]+', '', lower_item_name_illegal_characters)
                        if item_name in list_of_items_to_sell:
                            await click_window_by_path(self.client, path=item_path)
                            sell_button = await _maybe_get_named_window(self.client.root_window, 'sellAction')
                            if await sell_button.read_value_from_offset(688, 'bool') is True:
                                break
                            async with self.client.mouse_handler:
                                await self.client.mouse_handler.click_window(sell_button)
                                confirm_sale = await _maybe_get_named_window(self.client.root_window, 'leftButton')
                                await self.client.mouse_handler.click_window(confirm_sale)
                        else:
                            break
            else:
                pass

    async def select_tab_and_call_read_function(self):
        for tab in self.equippble_tab:
            await self.read_each_shop_item(tab)

    async def select_houseing_tab_and_call_read_function(self):
        async with self.client.mouse_handler:
            await self.client.mouse_handler.click_window_with_name('NextCategory_BackpackStuff')
        # Go to housing items tab and sell there.
        for tab in self.housing_tab:
            await self.read_each_shop_item(tab)












        