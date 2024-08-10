import asyncio
from time import time

from wizwalker import ClientHandler, Client, Keycode
from wizwalker.memory import MemoryReader, Window
from wizwalker.memory.memory_objects.fish import Fish, FishStatusCode
from wizwalker.extensions.scripting.utils import _maybe_get_named_window
from loguru import logger
from typing import Union, List



# Specifications ####################################
#IS_CHEST = True                                   #
#SCHOOL = "Any" # "Any" means you don't care         #
#RANK = 0  # 0 means you don't care                  #
#ID = 0 # 0 means you don't care                     #
#SIZE_MIN = 0 # 0 means you don't care               #
#SIZE_MAX = 999 # big number means you don't care    #
#ID = 1374007 # 0 means you don't care
# SIZE_MIN = 43.6 # 0 means you don't care               #
# SIZE_MAX = 999 # big number means you don't care    #
#####################################################





async def patch(client:Client) -> List[tuple[int, bytes]]:
    async def readbytes_writebytes(pattern:bytes, write_bytes:int) -> tuple[int, bytes]:
        add = await reader.pattern_scan(pattern, return_multiple=False)
        old_bytes = await reader.read_bytes(add, len(write_bytes))
        await reader.write_bytes(add, write_bytes)
        return (add, old_bytes)
    
    address_oldbytes = [] 
    reader = MemoryReader(client._pymem)
    
    async def scare_fish_patch():
        # scare fish patch
        num_nops = 5
        write_bytes = b"\x90" * num_nops
        pattern = rb"\xE8....\xEB.\x83\xF9\x04\x75.\xC7\x87" # E8 ?? ?? ?? ?? EB ?? 83 F9 04 75 ?? C7 87
        address_oldbytes.append(await readbytes_writebytes(pattern, write_bytes))
    
    async def bobber_submerison_rng_patch():
        # bobber submerison rng patch
        num_nops = 2
        write_bytes = b"\x90" * num_nops
        pattern = rb"\x7D\x37\xC7\x83........\xC7\x83" # 7D 37 C7 83 ?? ?? ?? ?? ?? ?? ?? ?? C7 83
        address_oldbytes.append(await readbytes_writebytes(pattern, write_bytes))
    
    async def fish_notice_bobber_instant_patch():
        # fish notice bobber instant patch
        num_nops = 6
        write_bytes = b"\x90" * num_nops
        pattern = rb"\x0F\x82....\xC7\x83........\x8B\x93" # 0F 82 ?? ?? ?? ?? C7 83 ?? ?? ?? ?? ?? ?? ?? ?? 8B 93
        address_oldbytes.append(await readbytes_writebytes(pattern, write_bytes))
    
    async def instant_fish():
        # patch instant fish
        num_nops = 2
        write_bytes = b"\x90" * num_nops
        pattern = rb"\x74\x63\x48\x8B\xCF\xE8....\x0F" #74 63 48 8B CF E8 ?? ?? ?? ?? 0F
        address_oldbytes.append(await readbytes_writebytes(pattern, write_bytes))
    
    async def instant_fish_2():
        # patch instant fish # 2 
        num_nops = 6
        write_bytes = b"\x90" * num_nops
        pattern = rb"\x0F\x82....\xF3\x44\x0F\x10\x0D....\x41\x0F\x2F\xC1" #0F 82 ?? ?? ?? ?? F3 44 0F 10 0D ?? ?? ?? ?? 41 0F 2F C1
        address_oldbytes.append(await readbytes_writebytes(pattern, write_bytes))
    
    async def instant_fish_3():
        # patch instant fish # 3
        num_nops = 6
        write_bytes = b"\x90" * num_nops
        pattern = rb"\x0F\x86....\xF3\x41\x0F\x5C\xF2" #0F 86 ?? ?? ?? ?? F3 41 0F 5C F2
        address_oldbytes.append(await readbytes_writebytes(pattern, write_bytes))
    
    async def instant_fish_4():
        # patch instant fish # 4
        num_nops = 6
        write_bytes = b"\x90" * num_nops
        pattern = rb"\x0F\x86....\x44\x0F\x2F\x05" #0F 86 ?? ?? ?? ?? 44 0F 2F 05
        address_oldbytes.append(await readbytes_writebytes(pattern, write_bytes))
    
    async def instant_fish_5():
        # patch instant fish # 5
        num_nops = 6
        write_bytes = b"\x90" * num_nops
        pattern = rb"\x0F\x84....\x48\x8B\x8B....\x45\x32" #0F 84 ?? ?? ?? ?? 48 8B 8B ?? ?? ?? ?? 45 32 
        address_oldbytes.append(await readbytes_writebytes(pattern, write_bytes))

    async def instant_fish_6():
        # patch instant fish # 6
        num_nops = 6
        write_bytes = b"\x90" * num_nops
        pattern = rb"\x0F\x84....\xF3\x0F\x10\x70\x6C\x0F\x28\xC6" #0F 84 ?? ?? ?? ?? F3 0F 10 70 6C 0F 28 C6
        address_oldbytes.append(await readbytes_writebytes(pattern, write_bytes))

    async def instant_fish_7():
        # patch instant fish # 7
        num_nops = 6
        write_bytes = b"\x90" * num_nops
        pattern = rb"\x0F\x86....\xF3\x0F\x10\x8B....\x0F\x28\xC1" #0F 86 ?? ?? ?? ?? F3 0F 10 8B ?? ?? ?? ?? 0F 28 C1
        address_oldbytes.append(await readbytes_writebytes(pattern, write_bytes))

    async def instant_fish_8():
        # patch instant fish # 8
        num_nops = 6
        write_bytes = b"\x90" * num_nops
        pattern = rb"\x0F\x86....\xF3\x0F\x10\x83....\xF3\x0F\x5C\x83" #0F 86 ?? ?? ?? ?? F3 0F 10 83 ?? ?? ?? ?? F3 0F 5C 83
        address_oldbytes.append(await readbytes_writebytes(pattern, write_bytes))
    
    async def instant_fish_9():
        # patch instant fish # 9
        num_nops = 6
        write_bytes = b"\x90" * num_nops
        pattern = rb"\x0F\x87....\xF2\x0F\x10\xB3....\xF2" #0F 87 ?? ?? ?? ?? F2 0F 10 B3 ?? ?? ?? ?? F2
        address_oldbytes.append(await readbytes_writebytes(pattern, write_bytes))
    
    async def skip_bobbing_patch():
        # skipping bobbing animation
        pattern = rb"\x0F\x82....\xF3\x0F\x11\x87" #0F 82 ?? ?? ?? ?? F3 0F 11 87
        write_bytes = b"\xE9\x79\x05\x00\x00\x90"
        address_oldbytes.append(await readbytes_writebytes(pattern, write_bytes))

    async def skip_catch_animation():
        pattern = rb"\x0F\x84....\x48..\x10\x02\x00\x00\xE8....\x84\xC0..\x48..\x78\x02\x00\x00\x00" #0F 84 ?? ?? ?? ?? 48 ?? ?? 10 02 00 00 E8 ?? ?? ?? ?? 84 C0 ?? ?? 48 ?? ?? 78 02 00 00 00
        write_bytes = b"\xE9\x88\x00\x00\x00\x90"
        address_oldbytes.append(await readbytes_writebytes(pattern, write_bytes))

    async def skip_struggle():
        num_nops = 6
        write_bytes = b"\x90" * num_nops
        pattern = rb"\x0F\x82....\x44..\xE4\x02\x00\x00\x48..\xC8\x02\x00\x00" # 0F 82 ?? ?? ?? ?? 44 ?? ?? E4 02 00 00 48 ?? ?? C8 02 00 00
        address_oldbytes.append(await readbytes_writebytes(pattern, write_bytes))

    patches = [
        scare_fish_patch(),
        bobber_submerison_rng_patch(),
        fish_notice_bobber_instant_patch(),
        instant_fish(),
        instant_fish_2(),
        instant_fish_3(),
        instant_fish_4(),
        instant_fish_5(),
        instant_fish_6(),
        instant_fish_7(),
        instant_fish_8(),
        instant_fish_9(),
        skip_bobbing_patch(),
        skip_catch_animation(),
        skip_struggle(),
    ]

    await asyncio.gather(*patches)

    return address_oldbytes

async def reset_patch(client: Client, address_bytes: List[tuple[int, bytes]]):
    reader = MemoryReader(client._pymem)
    for address, oldbytes in address_bytes:
        await reader.write_bytes(address, oldbytes)

async def window_exists(client, window_name: str, *, check_if_visible=True):
    w = await client.root_window.get_windows_with_name(window_name)
    if check_if_visible:
        return len(w) > 0 and await w[0].is_visible()
    else:
        return len(w) > 0

async def wait_for_window(client, window_name, *, timeout=10, check_if_visible=True):
    start = time()
    while not await window_exists(client, window_name, check_if_visible=check_if_visible):
        if time() - start >= timeout:
            break

async def wait_to_click_window_with_name(client: Client, window_name: str, *, timeout=10, check_if_visible=True):
    await wait_for_window(client, window_name, timeout=timeout, check_if_visible=check_if_visible)
    await asyncio.sleep(0.1)
    async with client.mouse_handler:
        await client.mouse_handler.click_window_with_name(window_name)

async def sell_basket(client: Client):
    await client.send_key(Keycode.V)
    while await window_exists(client, "Trash", check_if_visible=True):
        while not (await window_exists(client, "centerButton")):
            try:
                async with client.mouse_handler:
                    await client.mouse_handler.click_window_with_name("Trash")
            except ValueError:
                await asyncio.sleep(0.1)

        while await window_exists(client, "centerButton"):
            try:
                async with client.mouse_handler:
                    await client.mouse_handler.click_window_with_name("centerButton")
            except ValueError:
                await asyncio.sleep(0.1)

    await client.send_key(Keycode.V)

async def fetch_fish_list(fishing_manager):
    while True:
        try:
            return await fishing_manager.fish_list()
        except RuntimeError:
            await asyncio.sleep(0.1)

async def banish_config(fishing_manager, IS_CHEST, SCHOOL, RANK, ID, SIZE_MIN, SIZE_MAX):
    kept_fish = []
    for fish in await fetch_fish_list(fishing_manager):
        fish_temp = await fish.template()
        fish_is_accepted = True
        fish_size = await fish.size()
        if (await fish.is_chest()) != IS_CHEST:
            fish_is_accepted = False

        if (SCHOOL != "Any") and (await fish_temp.school_name() != SCHOOL):
            fish_is_accepted = False

        if (RANK != 0) and (await fish_temp.rank() != RANK):
            fish_is_accepted = False

        if (ID != 0) and (await fish.template_id() != ID):
            fish_is_accepted = False

        if fish_size < SIZE_MIN or fish_size > SIZE_MAX:
            fish_is_accepted = False

        if not fish_is_accepted:
            await fish.write_status_code(FishStatusCode.escaped)
        else:
            kept_fish.append(fish)
    return kept_fish

async def refresh_pond(client: Client, fishing_manager, IS_CHEST, SCHOOL, RANK, ID, SIZE_MIN, SIZE_MAX):
    fish_list = await banish_config(fishing_manager, IS_CHEST, SCHOOL, RANK, ID, SIZE_MIN, SIZE_MAX)
    while len(fish_list) == 0:
        fish_windows = await client.root_window.get_windows_with_name("FishingWindow")
        while len(fish_windows) == 0:
            async with client.mouse_handler:
                await client.mouse_handler.click_window_with_name("OpenFishingButton")
            fish_windows = await client.root_window.get_windows_with_name("FishingWindow")
            await asyncio.sleep(0.2)
        fish_window: Window = fish_windows[0]

        fish_sub_window = await fish_window.get_child_by_name("FishingSubWindow")
        bottomframe = await fish_sub_window.get_child_by_name("BottomFrame")
        icon2 = await bottomframe.get_child_by_name("Icon2")
        async with client.mouse_handler:
            await client.mouse_handler.click_window(icon2)

        while True:
            try:
                if len(await fetch_fish_list(fishing_manager)) > 0:
                    break
            except RuntimeError:
                await asyncio.sleep(0.1)
        await asyncio.sleep(.5)
        fish_list = await banish_config(fishing_manager)

async def fish_bot(client: Client, IS_CHEST: bool, SCHOOL: str, RANK: int, ID: int, SIZE_MIN: int, SIZE_MAX: int):
    address_bytes = []
    try:
        logger.debug(f'Preparing.')
        #await client.mouse_handler.activate_mouseless()
        address_bytes = await patch(client)
        logger.debug(f"Ready for Fish")

        fishing_manager = await client.game_client.fishing_manager()
        fish_caught = 0
        total = time()
        while True:
            start = time()
            # Awaiting the function causes it to close and not awaiting causes an awaiting error but still works. Un-commenting is up to you.
            # refresh_pond(client, fishing_manager, IS_CHEST, SCHOOL, RANK, ID, SIZE_MIN, SIZE_MAX)
            fish_list = await fetch_fish_list(fishing_manager)


            # Press Icon 1 (Lure)
            fish_windows = await client.root_window.get_windows_with_name("FishingWindow")

            while len(fish_windows) == 0:
                async with client.mouse_handler:
                    await client.mouse_handler.click_window_with_name("OpenFishingButton")
                fish_windows = await client.root_window.get_windows_with_name("FishingWindow")

            fish_window: Window = fish_windows[0]
            fish_sub_window = await fish_window.get_child_by_name("FishingSubWindow")
            bottomframe = await fish_sub_window.get_child_by_name("BottomFrame")
            icon1 = await bottomframe.get_child_by_name("Icon1")
            async with client.mouse_handler:
                await client.mouse_handler.click_window(icon1)
        
        

            # Check if fish hooked
            is_hooked = False
            basket_full = False
            while not is_hooked:
                if await window_exists(client, "MessageBoxModalWindow"):
                    await wait_to_click_window_with_name(client, "rightButton")
                    await sell_basket(client)
                    continue

                fish_list = await fetch_fish_list(fishing_manager)
                statuses = await asyncio.gather(*[fish.status_code() for fish in fish_list])
                for status in statuses:
                    if status == FishStatusCode.unknown2:
                        is_hooked = True
                        break
            
            if basket_full:
                continue

            # Invoke
            await client.send_key(Keycode.SPACEBAR)


            # Clear Fish Caught menu
            fish_failed = False
            timeout = time()
            while len(await client.root_window.get_windows_with_name("CaughtFishModalWindow")) == 0:
                if time() - timeout >= 10:
                    fish_failed = True
                    break
            
            if fish_failed:
                continue

            while len(await client.root_window.get_windows_with_name("CaughtFishModalWindow")) > 0:
                caught_window: Window = (await client.root_window.get_windows_with_name("CaughtFishModalWindow"))[0]
                caught_fish = await caught_window.get_child_by_name("CaughtFish")
                exit_button = await caught_fish.get_child_by_name("exit")
                async with client.mouse_handler:
                    await client.mouse_handler.click_window(exit_button)
                await asyncio.sleep(0.1)

            fish_caught += 1
            
            # Empty Basket
            if fish_caught % 100 == 0 and not IS_CHEST:
                await sell_basket(client)

            total_time = round((time() - total) / 60, 2)
            logger.debug(f"Fish Caught: {fish_caught}, Number of fish in pool: {len(fish_list) - 1}, Time: {total_time} minutes, Seconds per fish: {round((total_time / fish_caught) * 60, 2)}")

    finally:
        if address_bytes:
            await reset_patch(client, address_bytes)
        logger.debug("Closing")