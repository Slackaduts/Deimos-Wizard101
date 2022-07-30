from wizwalker import Client
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


async def get_chat(client: Client) -> List[str]:
    # Returns the text directly from the chat window
    if await is_visible_by_path(client, chat_window_path):
        chat_window = await get_window_from_path(client.root_window, chat_window_path)
        raw_chat_text = await chat_window.maybe_text()
        chat_list = raw_chat_text.splitlines()
        return chat_list

    else:
        return []


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


async def logging_loop(client: Client):
    # TODO: Finish this loop and create a system for determining new drops

    latest_drop: str = None

    while True:
        await asyncio.sleep(1)

        chat_text = await get_chat(client)
        temp_drops = filter_drops(chat_text)
        temp_drops.reverse()

        if temp_drops:
            latest_temp_drop = temp_drops[0]

            if latest_temp_drop != latest_drop:
                client.latest_drops: List[str] = []

                for drop in temp_drops:
                    if drop != latest_drop and latest_drop:
                        client.latest_drops.append(drop)

                    else:
                        break

                client.latest_drops.reverse()
                if latest_drop:
                    [logger.debug(f'New Drop: {drop}') for drop in client.latest_drops]

                latest_drop = latest_temp_drop
