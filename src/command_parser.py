from importlib.resources import path
from typing import List, Tuple, Coroutine
import asyncio
from wizwalker import Client, XYZ
from src.gui_inputs import param_input
from src.utils import use_potion, buy_potions, is_free, logout_and_in, wait_for_visible_by_path, click_window_by_path, attempt_activate_mouseless, attempt_deactivate_mouseless
from src.teleport_math import YPR, write_ypr
import re

# THIS WHOLE THING IS UNFINISHED - slack

async def parse_input(client: Client, clients: List[Client], raw_commands: str, line_seperator: str = '\n'):
    # Calls wizwalker functions based on text commands in the GUI.
    command_list = raw_commands.split(line_seperator)


def parse_number(input_str: str, default: float) -> float:
    if '(' in input_str:
        input_str = input_str.strip('()')

        return param_input(input_str, default)

    else:
        return float(input_str)


async def parse_location(client: Client, location_str: str, use_camera: bool = False) -> Tuple[XYZ, YPR]:
    if '(' in location_str:
        location_str_cut: str = re.findall('\([^\)]+\)')[0]
        location = location_str_cut.split(', ')

    else:
        location = ['quest']

    location_type = location_str.split(' ')[0]

    xyz = XYZ
    ypr = YPR

    if 'quest' not in location:
        if use_camera:
            camera = await client.game_client.selected_camera_controller()
            default_xyz = await camera.position()
            default_ypr = YPR(await camera.yaw(), await camera.pitch(), await camera.roll())
        else:
            default_xyz = await client.body.position()
            default_ypr = YPR(await client.body.yaw(), await client.body.pitch(), await client.body.roll())

        if 'xyz' in location_type.lower():
            xyz = XYZ(parse_number(location[0], default_xyz.x), parse_number(location[1], default_xyz.y), parse_number(location[2], default_xyz.z))

            if 'ypr' in location_type.lower():
                ypr = YPR(parse_number(location[3], default_ypr.y), parse_number(location[4], default_ypr.p), parse_number(location[5], default_ypr.r))

        elif 'ypr' in location_type.lower():
            ypr = YPR(parse_number(location[0], default_ypr.y), parse_number(location[1], default_ypr.p), parse_number(location[2], default_ypr.r))

    else:
        xyz = await client.quest_position.position()

    return (xyz, ypr)


def client_from_titles(clients: List[Client], title_str: str = 'p1') -> Client:
    return [client for client in clients if client.title.lower() == title_str][0]


async def wait_for_coro(coro: Coroutine, wait_for_not: bool = False, interval: float = 0.25):
    if wait_for_not:
        while await coro():
            await asyncio.sleep(interval)

    else:
        while not await coro():
            await asyncio.sleep(interval)


def find_path(input_str: str) -> List[str]:
    path_str: str = re.findall('(?<=\[).+?(?=\])', input_str)[0]
    path_str = path_str.replace(' ', '')
    window_path = path_str.split(',')

    return window_path


async def parse_command(clients: List[Client], commands: str):
    split_command = commands.split(' ')
    if split_command[-1].lower() == 'mass':
        mass = True
        desired_client = client_from_titles(clients)

    else:
        mass = False
        client_str = split_command[-1]
        if client_str[0].lower() == 'p' and client_str[2].isdigit():
            desired_client = client_from_titles(clients, split_command[-1])

        else:
            desired_client = client_from_titles(clients)

    match split_command[0].lower():
        case 'freecam':
            await desired_client.camera_swap() if mass else await asyncio.gather(*[client.camera_swap() for client in clients])

        case 'use_potion':
            await use_potion(desired_client) if mass else await asyncio.gather(*[use_potion(client) for client in clients])

        case 'buy_potions':
            await buy_potions(desired_client) if mass else await asyncio.gather(*[buy_potions(client) for client in clients])

        case 'speed':
            default_speed = await desired_client.client_object.speed_multiplier()
            await desired_client.client_object.write_speed_multiplier(parse_number(split_command[1], default_speed)) if mass else await asyncio.gather(*[client.client_object.write_speed_multiplier(parse_number(split_command[1], default_speed)) for client in clients])

        case 'teleport':
            xyz, ypr = await parse_location(desired_client, ' '.join(split_command[2L]))
            await desired_client.teleport(xyz) if mass else await asyncio.gather(*[client.teleport(xyz) for client in clients])
            await write_ypr(desired_client, ypr) if mass else await asyncio.gather(*[write_ypr(client, ypr) for client in clients])

        case 'walk_to':
            xyz, _ = await parse_location(desired_client, split_command[1])
            await desired_client.goto(xyz.x, xyz.y) if mass else await asyncio.gather(*[client.goto(xyz.x, xyz.y) for client in clients])

        case 'wait_for_combat':
            await wait_for_coro(desired_client.in_battle) if mass else await asyncio.gather(*[wait_for_coro(client.in_battle) for client in clients])

            if len(split_command) >= 2 and split_command[1].lower() == 'completion':
                await wait_for_coro(desired_client.in_battle, True) if mass else await asyncio.gather(*[wait_for_coro(client.in_battle, True) for client in clients])

        case 'wait_for_zone_change':
            await desired_client.wait_for_zone_change() if mass else await asyncio.gather(*[client.wait_for_zone_change() for client in clients])

            if len(split_command) >= 2 and split_command[1].lower() == 'completion':
                await wait_for_coro(desired_client.is_loading) if mass else await asyncio.gather(*[wait_for_coro(client.is_loading) for client in clients])

        case 'wait_for_dialogue' | 'wait_for_dialog':
            await wait_for_coro(desired_client.is_in_dialog) if mass else await asyncio.gather(*[wait_for_coro(client.is_in_dialog) for client in clients])
            if len(split_command) >= 2 and split_command[1].lower() == 'completion':
                await wait_for_coro(desired_client.is_in_dialog, True) if mass else await asyncio.gather(*[wait_for_coro(client.is_in_dialog, True) for client in clients])

        case 'wait_for_free':
            async def _wait_for_free(client: Client, wait_for_not: bool = False, interval: float = 0.25):
                if wait_for_not:
                    while await is_free(client):
                        await asyncio.sleep(interval)

                else:
                    while not await is_free(client):
                        await asyncio.sleep(interval)

            await _wait_for_free(desired_client) if mass else await asyncio.gather(*[_wait_for_free(client) for client in clients])

            if len(split_command) >= 2 and split_command[1].lower() == 'completion':
                await _wait_for_free(desired_client, True) if mass else await asyncio.gather(*[_wait_for_free(client, True) for client in clients])

        case 'relog' | 'logout_and_in':
            await logout_and_in(desired_client) if mass else await asyncio.gather(*[logout_and_in(client) for client in clients])

        case 'wait_for_visible':
            window_path = find_path(commands)

            await wait_for_visible_by_path(desired_client, window_path) if mass else await asyncio.gather(*[wait_for_visible_by_path(client, window_path) for client in clients])

            if len(split_command) >= 2 and split_command[1].lower() == 'completion':
                await wait_for_visible_by_path(desired_client, window_path, True) if mass else await asyncio.gather(*[wait_for_visible_by_path(client, window_path, True) for client in clients])

        case 'click_window':
            window_path = find_path(commands)
            if len(split_command) >= 2 and split_command[1].lower() == 'hooks':
                hooks = True

            else:
                hooks = False

            await click_window_by_path(desired_client, window_path, hooks) if mass else await asyncio.gather(*[click_window_by_path(client, window_path, hooks) for client in clients])

        case 'click' | 'right_click':
            if split_command[0].lower() == 'right_click':
                right_click = True

            else:
                right_click = False

            if len(split_command) >= 4 and split_command[1].lower() == 'hooks':
                await attempt_activate_mouseless(desired_client) if mass else await asyncio.gather(*[attempt_activate_mouseless(client) for client in clients])

                location = parse_location(desired_client, commands)
                await desired_client.mouse_handler.click(int(location.x), int(location.y), right_click=right_click)

                await attempt_deactivate_mouseless(desired_client) if mass else await asyncio.gather(*[attempt_deactivate_mouseless(client) for client in clients])

        case 'mouseless':
            if len(split_command) >= 2:
                on_words = ['on', 'true', 'hook']
                if split_command[1].lower() in on_words:
                    await attempt_activate_mouseless(desired_client) if mass else await asyncio.gather(*[attempt_activate_mouseless(client) for client in clients])

                else:
                    await attempt_deactivate_mouseless(desired_client) if mass else await asyncio.gather(*[attempt_deactivate_mouseless(client) for client in clients])

            else:
                await attempt_activate_mouseless(desired_client) if mass else await asyncio.gather(*[attempt_activate_mouseless(client) for client in clients])

        case 'wait':
            await asyncio.sleep(float(split_command[1]))