import re
import operator as op
from wizwalker.extensions.scripting.utils import _maybe_get_named_window
from wizwalker.errors import MemoryReadError
from src.utils import *
import asyncio
from wizwalker.client_handler import ClientHandler
import pyperclip

class ParsePack:
    def __init__(self, client: "Client"):
        self.client = client
        self.spell_book_is_open = None
        self.inventory_page = None

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

    @staticmethod
    def remove_special_chars(text):
        pattern = r'[^a-zA-Z0-9, ]+'
        cleaned_text = re.sub(pattern, '', text)
        return cleaned_text

    async def attempt_to_close_all_windows(self) -> None:
        # Logic for attempting to close:
        # 2nd spellbook page being opened, shop window being open, and final spell book being open.
        try:
            try:
                async with self.client.mouse_handler:
                    await self.client.mouse_handler.click_window_with_name('Close_Button')
                await asyncio.sleep(1)
            except ValueError:
                logger.debug(f"Client {self.client.title} - Attempted to close inventory window that didn't exist")
            try:
                async with self.client.mouse_handler:
                    await self.client.mouse_handler.click_window_with_name('exit')
                await asyncio.sleep(1)
            except ValueError:
                logger.debug(f"Client {self.client.title} - Attempted to close inventory window that didn't exist")
            try:
                async with self.client.mouse_handler:
                    await self.client.mouse_handler.click_window_with_name('Close_Button')
                await asyncio.sleep(1)
            except ValueError:
                logger.debug(f"Client {self.client.title} - Attempted to close inventory window that didn't exist")
        except ValueError:
            logger.debug(f'Client {self.client.title} - Attempted to close inventory windows')

    async def open_and_select_backpack_all_tab(self) -> str:
        def reg(m):
            return m.group(1)
        await self.attempt_to_close_all_windows()
        # General Logic for detecting if spell book is open, if it's open we need to make sure its on the right tab
        # To Keep it simple, we are starting on Backpack tab, moving to Housing, and Finally Jewels (for now at least)
        # If spell book is not open, it returns none. We go into the "none if statement" and open the spellbook
        if not await self._check_if_window_is_visible('DeckConfiguration'):
            # print('Spell book not open, manually opening spellbook')
            spellbook = await _maybe_get_named_window(self.client.root_window, "btnSpellbook")
            async with self.client.mouse_handler:
                await self.client.mouse_handler.click_window(spellbook)
            await asyncio.sleep(.2)
        # If current page isnt inventory page it returns none. We go into the "none if-statement" and open the inventory
        if not await self._check_if_window_is_visible('InventorySpellbookPage'):
            # print('Current page is not backpack, switch to backpack page')
            select_inventory_tab = await _maybe_get_named_window(self.client.root_window, "Inventory")
            async with self.client.mouse_handler:
                await self.client.mouse_handler.click_window(select_inventory_tab)
            await asyncio.sleep(.5)
        try:
            quick_sell_tab = await _maybe_get_named_window(self.client.root_window, "QuickSell_Item")
        except ValueError:
            # Clicked too quick
            await asyncio.sleep(3)
            quick_sell_tab = await _maybe_get_named_window(self.client.root_window, "QuickSell_Item")
        # I don't think we can detect if the user is on the 'All Equipments Tab', so we just click it no matter what
        async with self.client.mouse_handler:
            await self.client.mouse_handler.click_window(quick_sell_tab)
        await asyncio.sleep(1)

        select_all_tab = await _maybe_get_named_window(self.client.root_window, 'ShopCategory_All')
        async with self.client.mouse_handler:
            await self.client.mouse_handler.click_window(select_all_tab)
        await asyncio.sleep(.2)

        # Check what page the user is on. If they aren't on the first page, set them to the first page
        left_button = await _maybe_get_named_window(self.client.root_window, 'leftscroll')
        right_button = await _maybe_get_named_window(self.client.root_window, 'rightscroll')

        dupped_list_of_inventory_items = []
        if await left_button.is_visible():
            while not await is_control_grayed(left_button):
                async with self.client.mouse_handler:
                    await asyncio.sleep(.2)
                    await self.client.mouse_handler.click_window(left_button)
        while not await is_control_grayed(right_button):
            async with self.client.mouse_handler:
                await asyncio.sleep(.2)
                await self.read_each_item()
                list_of_inventory_items = await self.read_each_item()
                dupped_list_of_inventory_items.append(list_of_inventory_items)
                await self.client.mouse_handler.click_window(right_button)
        # Below reads final page contents. The while loop breaks, and we want to read the final page of items.
        list_of_inventory_items = await self.read_each_item()
        await asyncio.sleep(.2)
        dupped_list_of_inventory_items.append(list_of_inventory_items)
        master_list_of_inventory_items_with_dupes = []
        master_list_of_inventory_items_without_dupes = []
        # Removing items that are duplicates, we only need one copy in the list of items we sell
        for i in dupped_list_of_inventory_items:
            if op.countOf(dupped_list_of_inventory_items, i) >= 1 and (i not in master_list_of_inventory_items_with_dupes):
                master_list_of_inventory_items_with_dupes.append(i)
        # paperclip doesn't like lists, so we convert it to a sting
        messy_master_string_of_inventory_items: str = ','.join(map(str, master_list_of_inventory_items_with_dupes))

        __master_string_of_inventory_items = self.remove_special_chars(messy_master_string_of_inventory_items)
        _master_string_of_inventory_items = __master_string_of_inventory_items.replace(', ', ',')
        master_string_of_inventory_items = _master_string_of_inventory_items.replace(' ,', ',')
        correctly_combined_list_of__duped_items = master_string_of_inventory_items.split(",")
        for i in correctly_combined_list_of__duped_items:
            if op.countOf(correctly_combined_list_of__duped_items, i) >= 1 and (i not in master_list_of_inventory_items_without_dupes):
                master_list_of_inventory_items_without_dupes.append(i)

        # We loved that above cancer to remove special characters, so let's do it again! I could do this better, but it works sooooooo
        master_string_of_inventory_items_without_dupes: str = ','.join(map(str, master_list_of_inventory_items_without_dupes))
        __master_string_of_inventory_items_without_dupes = self.remove_special_chars(master_string_of_inventory_items_without_dupes)
        _master_string_of_inventory_items_without_dupes = __master_string_of_inventory_items_without_dupes.replace(', ', ',')
        master_string_of_inventory_items_without_dupes = _master_string_of_inventory_items_without_dupes.replace(' ,', ',')

        pyperclip.copy(master_string_of_inventory_items_without_dupes)
        logger.debug(f'Client {self.client.title} - copied items in backpack to clipboard, if you want to manually add every item')
        async with self.client.mouse_handler:
            await self.client.mouse_handler.click_window_with_name('exit')
        async with self.client.mouse_handler:
            await self.client.mouse_handler.click_window_with_name('Close_Button')
        return master_string_of_inventory_items_without_dupes

    async def read_each_item(self) -> list:
        list_of_items_in_inventory_dupes = []
        for i in range(0, 10):
            # We set the path for 'i' which is the item we want to check if we can sell it
            item = await get_window_from_path(self.client.root_window, ["WorldView", "shopGUI", "buyWindow", "column0", f"shoplist{i}"])
            # We set the mouse position over the item to read the meta data of the item
            # messy_item_name = await item.read_wide_string_from_offset(616)
            try:
                messy_item_name = await item.read_wide_string_from_offset(616)
            except MemoryReadError:
                # The item 'Litter' breaks this code above, why I have no clue why, but we get memory error, so we go to fall back?
                hovered_item = await get_window_from_path(self.client.root_window, ['WorldView', 'shopGUI', 'buyWindow', 'column0', f"shoplist{i}"])
                async with self.client.mouse_handler:
                    await self.client.mouse_handler.set_mouse_position_to_window(hovered_item)
                new_item_path = await get_window_from_path(self.client.root_window, ['WorldView', 'compareNewItem', 'ControlWidget', 'mainLayout'])
                stats = await new_item_path.children()
                for stat in stats:
                    # Read each value in stats: Contains, Name, Link to image.jpg, and Stat, and we only want the
                    stat_text_lower = (await stat.maybe_text()).lower()
                    if "<center><color;ffffff00>" in stat_text_lower:
                        _messy_item_name = stat_text_lower.split("<center><color;ffffff00>", 1)[1]
                        if _messy_item_name == '':
                            break
                        # I print this debug because I want to search for items that cause this error
                        # I want to find out why they cause this error??
                        logger.debug(f"Client {self.client.title} - {_messy_item_name} in backpack caused MemoryReadError, Try:Except handled it")
                        break
            if messy_item_name == '':
                pass
            else:
                lower_item_name_illegal_characters = messy_item_name.lower()
                item_name = re.sub('[^A-Za-z0-9 ]+', '', lower_item_name_illegal_characters)
                list_of_items_in_inventory_dupes.append(item_name)
        # list_of_items_in_inventory = dict.fromkeys(list_of_items_in_inventory_dupes)
        # return list_of_items_in_inventory
        return list_of_items_in_inventory_dupes


        