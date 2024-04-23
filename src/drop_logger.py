from wizwalker import Client
from wizwalker.memory.memory_objects.window import Window
from src.utils import get_window_from_path, is_visible_by_path
from src.paths import chat_window_path
from typing import List
from loguru import logger
import re
import asyncio

# CREDIT TO AARON FOR IMPLEMENTING THIS ORIGINALLY, IM REDOING HIS IMPLEMENTATION HERE -slack

drop_types = [
    'PetSnack',
    'Reagent',
    'Housing',
    'Pet',
    'Shoes',
    'Seed',
    'Jewel',
    'Robe',
    'Hat',
    'Athame',
    'Weapon',
    'Deck',
    'Ring',
    'Amulet',
]


async def get_chat(client: Client) -> str:
    # Returns the text directly from the chat window
    if await is_visible_by_path(client, chat_window_path):
        chat_window = await get_window_from_path(client.root_window, chat_window_path)
        if chat_window:
            raw_chat_text = await chat_window.maybe_text()
            return raw_chat_text

        else:
            return ''

    else:
        return ''


def filter_drops(input_list: List[str]) -> List[str]:
    # Takes in a list of chat window text and only returns the item drops.
        drops = []
        for raw_i in input_list.copy():
            # Ensures this message came from the system and not another player, it's safe to assume no player will ever say this
            if 'Art_Chat_System.dds' in raw_i:
                # Matches everything after "> <"
                i = re.findall('(?<=> <).*|$', raw_i)[0]

                if i:
                    # Matches everything after ; and before >, excluding both
                    if ';' in i:
                        drop_type: str = re.findall('(?<=;).*?[^>]*|$', i)[0]

                    if drop_type in drop_types:
                        # Match everything in between > <
                        raw_drop: str = re.findall('>.*?<|$', i)[0]
                        # Remove arrow brackets
                        drop: str = re.findall('[^>]+[^<]+|$', raw_drop)[0]
                        drop = drop.replace(' ', '', 1)
                        drops.append(drop)

                elif ':' in raw_i.lower():
                    # Matches everything after : and before >, excluding both
                    drop: str = re.findall('(?<=:).*?[^<]*|$', raw_i)[0]
                    drop = drop.replace(' ', '', 1)
                    drops.append(drop)
        return drops

def stuff_finder(A, B):
    for item in A:
        if item in B:
            index = B.index(item)
            B = B[index + 1:]
    return B

##### OLD FUNCTION #####

# def find_new_stuff(old: str, new: str) -> str:
#     # CREDIT TO SIROLAF FOR THIS FUNCTION
# 	found_idx = -1

# 	while True:
# 		found_idx = new.find(old)
# 		if found_idx >= 0:
# 			break
# 		old = old[1:]
# 		if len(old) == 0:
# 			break

# 	if found_idx < 0:
# 		return new # entire string is new
# 	return new[found_idx+len(old):]

async def logging_loop(client: Client, toSearch=[]):
    # TODO: Finish this loop and create a system for determining new drops
    if toSearch:
        toSearch = toSearch.split('\n')
    while True:
        chat_text = await get_chat(client)
        await asyncio.sleep(1)

        if chat_text:
            temp_drops = filter_drops(chat_text.split('\n'))
            new_drops = stuff_finder(client.latest_drops.split('\n'), temp_drops)

            if not client.latest_drops:
                client.latest_drops = '\n'.join(temp_drops)
            
            elif new_drops:
                # If custom drop logging is provided
                if toSearch:
                     new_drops_set = set(new_drops)
                     toSearch_set = set(toSearch)
                     new_drops_set = new_drops_set.intersection(toSearch_set)
                     client.latest_drops = '\n'.join(temp_drops)
                     for drop in new_drops_set:
                        logger.debug(f'{client.title} - Recorded Drop: {drop}')
                # If no custom drop logging is provided
                else:
                    client.latest_drops = '\n'.join(temp_drops)
                    for drop in new_drops:
                        logger.debug(f'{client.title} - New Drop: {drop}')