import traceback
from asyncio import CancelledError
from typing import Dict, List, Tuple, Coroutine
import asyncio
from wizwalker import Client, XYZ, Orient, Keycode
from wizwalker.errors import HookNotActive
from wizwalker.extensions.wizsprinter.wiz_navigator import toZone
from wizwalker.memory.memory_objects.camera_controller import CameraController

from src.sprinty_client import SprintyClient
from src.gui_inputs import is_numeric, param_input
from src.utils import read_webpage, index_with_str, get_window_from_path, teleport_to_friend_from_list, auto_potions_force_buy, use_potion, is_free, logout_and_in, click_window_by_path, wait_for_visible_by_path, refill_potions, refill_potions_if_needed, wait_for_zone_change
from src.camera_utils import glide_to, point_to_xyz, rotating_glide_to, orbit
from src.tokenizer import tokenize
# from src.collision_math import plot_cube
import re
from loguru import logger


async def parse_location(split_command: List[str], camera: CameraController = None, client: Client = None) -> Tuple[List[XYZ], List[Orient]]:
    # Takes in a camera or client along with a command string, and returns the location. Uses the same input parsing the GUI does, allowing for equation support.
    split_command = [s.lower().replace(', ', '') for s in split_command.copy()]
    xyzs: List[XYZ] = []
    orientations: List[Orient] = []

    if camera:
        default_xyz = await camera.position()
        default_orientation = await camera.orientation()

    else:
        default_xyz = await client.body.position()
        default_orientation = await client.body.orientation()

    for arg in split_command:
        if 'xyz' in arg:
            split_arg = arg.replace('xyz(', '').strip(')').split(',')
            xyzs.append(XYZ(
                param_input(split_arg[0], default_xyz.x),
                param_input(split_arg[1], default_xyz.y),
                param_input(split_arg[2], default_xyz.z)
            ))

        elif 'orient' in arg:
            split_arg = arg.replace('orient(', '').strip(')').split(',')
            orientations.append(Orient(
                param_input(split_arg[0], default_orientation.pitch),
                param_input(split_arg[1], default_orientation.roll),
                param_input(split_arg[2], default_orientation.yaw)
            ))

    return (xyzs, orientations)


def handle_index(input_list, i: int = 0, default = None):
    if len(input_list) <= i:
        return default

    else:
        return input_list[i]


def client_from_titles(clients: List[Client], title_str: str = 'p1') -> Client:
    # Returns a Client object based off matching the window title.
    return [client for client in clients if client.title.lower() == title_str][0]


async def wait_for_coro(coro: Coroutine, wait_for_not: bool = False, interval: float = 0.25):
    # Waits for a Coroutine to return True, or return False if wait_for_not is True.
    if wait_for_not:
        while await coro():
            await asyncio.sleep(interval)

    else:
        while not await coro():
            await asyncio.sleep(interval)


# def find_path(commands: List[str], starting_index: int = 2) -> List[str]:
#     # Finds the window path string from a list of strings
#     relevant_strings: List[str] = commands[starting_index:]
#     path_str: str = re.findall('\[(.*?)\]|$', ','.join(relevant_strings))[0]
#     desired_path: List[str] = path_str.strip('[]"').replace("'", "").split(',')

#     return desired_path


# def split_line(l: str) -> list[str]:
#     result = []

#     in_nested = False
#     word = ''
#     for c in l:
#         match c:
#             case '(':
#                 in_nested = True
#             case ')':
#                 in_nested = False
#             case ' ' | ',':
#                 if not in_nested:
#                     if len(word) > 0:
#                         result.append(word)
#                     word = ''
#                     c = ''
#         word += c
#     result.append(word)

#     if in_nested:
#         raise Exception("Unterminated (")

#     return result


async def parse_command(clients: List[Client], command_str: str):
    # Executes a single raw command string for the bot creator.
    all_clients = clients.copy()
    command_str = command_str.replace(', ', ',')

    check_strings = ['tozone', 'to_zone', 'waitforzonechange', 'wait_for_zone_change']
    # remove _ from command_str except for a few commands that it interferes with
    if not any(substring in command_str for substring in check_strings):
        command_str = command_str.replace('_', '')

    split_command = tokenize(command_str)

    if not split_command:
        return

    match split_command[0].lower():
        case 'kill' | 'killbot' | 'stop' | 'stopbot' | 'end' | 'exit':
            # Kills the bot loop, useful for not having stuff loop
            logger.debug('Bot Killed')
            raise CancelledError

        case 'sleep' | 'wait' | 'delay':
            # Delays a specified number of seconds
            await asyncio.sleep(float(split_command[-1]))

        case 'log' | 'debug' | 'print':
            # Logs a specific message or prints the text of a window (by path, if any)
            if len(split_command) >= 3 and split_command[1].lower() == 'window' and type(split_command[2]) == list:
                for client in clients:
                    desired_window = await get_window_from_path(client.root_window, split_command[2])
                    relevant_string = await desired_window.maybe_text()
                    logger.debug(f'{client.title} - {relevant_string}')

            else:
                relevant_string: str = ' '.join(split_command[1:])
                logger.debug(relevant_string)

        case _:
            client_str = split_command[0].replace(' ', '')
            exclude = False
            if 'except' in client_str:
                split_command.pop(0)
                client_str = split_command[0]
                exclude = True

            if 'mass' not in client_str:
                # Allows for specific clients to be used via a : seperator. Example: p1:p3:p4   , except p2
                if ':' in client_str:
                    split_clients = client_str.split(':')
                    provided_clients = [client_from_titles(all_clients.copy(), title) for title in split_clients]
                else:
                    provided_clients = [client_from_titles(all_clients, client_str)]

                if is_numeric(client_str[1]):
                    if exclude:
                        # Sets client list equal to all clients except specified ones
                        clients = [client for client in all_clients.copy() if client not in provided_clients]
                    else:
                        clients = provided_clients

            match split_command[1].lower():

                case 'teleport' | 'tp' | 'setpos':
                    # Raw TP, not navmap TP due to some limitations with navmap TP
                    match split_command[2]:
                        case 'closestmob' | 'mob':
                            await asyncio.gather(*[SprintyClient(p).tp_to_closest_mob() for p in clients])

                        case 'quest' | 'questpos' | 'questposition':
                            await asyncio.gather(*[p.teleport(await clients[0].quest_position.position()) for p in clients])

                        case _:
                            client_location = None
                            for p in all_clients:
                                if p.title == split_command[2]:
                                    client_location = await p.body.position()
                                    await asyncio.gather(*[client.teleport(client_location) for client in clients])
                                    break

                            # a client title was not provided - user likely listed an actual XYZ coordinate
                            if client_location is None:
                                xyzs = []
                                for client in clients:
                                    client_xyzs, _ = await parse_location(split_command, client=client)
                                    xyzs.append(client_xyzs[0])

                                await asyncio.gather(*[client.teleport(xyz) for client, xyz in zip(clients, xyzs)])

                case 'walkto' | 'goto':
                    # Walks in a straight line to a given XYZ (Z agnostic)
                    xyzs = []
                    for client in clients:
                        client_xyzs, _ = await parse_location(split_command, client=client)
                        xyzs.append(client_xyzs[0])
                    await asyncio.gather(*[client.goto(xyz.x, xyz.y) for client, xyz in zip(clients, xyzs)])

                case 'sendkey' | 'press' | 'presskey':
                    # Sends a key press
                    key = split_command[2]
                    time = 0.1
                    if len(split_command) >= 4:
                        time = float(split_command[3])

                    await asyncio.gather(*[client.send_key(Keycode[key], time) for client in clients])

                case 'waitfordialog' | 'waitfordialogue':
                    # Waits for dialogue window to appear
                    await asyncio.gather(*[wait_for_coro(client.is_in_dialog) for client in clients])

                    if split_command[1].lower() == 'completion':
                        # Waits for dialogue window to disappear
                        await asyncio.gather(*[wait_for_coro(client.is_in_dialog, True) for client in clients])

                case 'waitforbattle' | 'waitforcombat':
                    # Waits for combat
                    await asyncio.gather(*[wait_for_coro(client.in_battle) for client in clients])

                    if split_command[-1].lower() == 'completion':
                        # Waits for combat to end
                        await asyncio.gather(*[wait_for_coro(client.in_battle, True) for client in clients])

                case 'waitforzonechange' | 'wait_for_zone_change':
                    # waits for zone to change from the provided zone name
                    if split_command[-2].lower() == 'from':
                        await asyncio.gather(*[wait_for_zone_change(client, current_zone=split_command[-1]) for client in clients])
                    # waits for zone to change to the provided zone name
                    elif split_command[-2].lower() == 'to':
                        await asyncio.gather(*[wait_for_zone_change(client, to_zone=split_command[-1]) for client in clients])
                    else:
                        # Waits for the zone to change
                        await asyncio.gather(*[client.wait_for_zone_change() for client in clients])

                        if split_command[-1].lower() == 'completion':
                            # Waits for loading screen to end
                            await asyncio.gather(*[wait_for_coro(client.is_loading, True) for client in clients])

                case 'waitforfree':
                    # Waits for is_free to return True
                    async def _wait_for_free(client: Client, wait_for_not: bool = False, interval: float = 0.25):
                        if wait_for_not:
                            while await is_free(client):
                                await asyncio.sleep(interval)

                        else:
                            while not await is_free(client):
                                await asyncio.sleep(interval)

                    await asyncio.gather(*[_wait_for_free(client) for client in clients])

                    if split_command[-1].lower() == 'completion':
                        # Waits for is_free to return False
                        await asyncio.gather(*[_wait_for_free(client, True) for client in clients])

                case 'usepotion':
                    # Uses a potion
                    if len(split_command) > 3:
                        # Same, but uses specified mana/health thresholds
                        await asyncio.gather(*[SprintyClient(p).use_potion_if_needed(health_percent=int(split_command[2]), mana_percent=int(split_command[3]), handle_hooks=True) for p in clients])
                    else:
                        await asyncio.gather(*[use_potion(client) for client in clients])

                case 'buypotions' | 'refillpotions' | 'buypots' | 'refillpots':
                    # Refills potions
                    if len(split_command) > 2:
                        # Refills potions if needed
                        if split_command[2] == 'ifneeded':
                            await asyncio.gather(*[refill_potions_if_needed(client) for client in clients])
                    else:
                        await asyncio.gather(*[refill_potions(client, mark=True, recall=True) for client in clients])

                case 'logoutandin' | 'relog':
                    # Logs out the specific clients, and logs them back in
                    await asyncio.gather(*[logout_and_in(client) for client in clients])

                case 'click':
                    # Clicks at a specified screen XY
                    async def command_parser_click_mouse_handler(client):
                        async with client.mouse_handler:
                            await client.mouse_handler.click(int(split_command[2], int(split_command[3])))
                        
                    await asyncio.gather(*[command_parser_click_mouse_handler(client) for client in clients])


                case 'clickwindow':
                    # Clicks a specific window by path
                    await asyncio.gather(*[click_window_by_path(client, split_command[2], True) for client in clients])

                case 'waitforwindow' | 'waitforpath':
                    # Waits for a specific window (by path) to be visible
                    await asyncio.gather(*[wait_for_visible_by_path(client, split_command[2]) for client in clients])
                    if type(split_command[-1]) == str and split_command[-1].lower() == 'completion':
                        # Waits for a specific window (by path) to not be visible
                        await asyncio.gather(*[wait_for_visible_by_path(client, split_command[2], True) for client in clients])

                case 'friendtp' | 'friendteleport':
                    # Teleports specified clients to another via wizard name or icon
                    await asyncio.sleep(.25)

                    if split_command[2] == 'icon':
                        # uses fish icon
                        async def teleport_to_friend_from_list_fish_icon_mouse_handler(client):
                            await teleport_to_friend_from_list(client, icon_list=2, icon_index=0)
                            
                        await asyncio.gather(*[teleport_to_friend_from_list_fish_icon_mouse_handler(client) for client in clients])
                        
                    else:
                        # uses provided wizard name
                        async def teleport_to_friend_from_list_wizard_name_mouse_handler(client):
                            async with client.mouse_handler:
                                await teleport_to_friend_from_list(client, name=' '.join(split_command[2:]))
                            
                        await asyncio.gather(*[teleport_to_friend_from_list_wizard_name_mouse_handler(client) for client in clients])


                case 'entitytp' | 'entityteleport':
                    # Teleports to a specific entity by vague name
                    await asyncio.gather(*[SprintyClient(client).tp_to_closest_by_vague_name(split_command[2]) for client in clients])

                case 'tozone' | 'to_zone':
                    # Navigates to a specific zone, by vague name
                    zoneChanged = await toZone(clients, split_command[2])

                    if zoneChanged == 0:
                        logger.debug('Reached destination zone: ' + await clients[0].zone_name())
                    else:
                        logger.error('Failed to go to zone.  It may be spelled incorrectly, or may not be supported.')

                # case 'col':
                #     await plot_cube(clients[0])

                case _:
                    await asyncio.sleep(0.25)

    await asyncio.sleep(0)


async def execute_flythrough(client: Client, flythrough_data: str, line_seperator: str = '\n'):
    flythrough_actions = flythrough_data.split(line_seperator)

    web_command_strs = ['webpage', 'pull', 'embed']
    new_commands = []

    for command_str in flythrough_actions:
        command_tokens = tokenize(command_str)

        if command_tokens[0].lower() in web_command_strs:
            web_commands = read_webpage(command_tokens[1])
            new_commands.extend(web_commands)

        else:
            new_commands.append(command_str)

    if not await client.game_client.is_freecam():
        await client.camera_freecam()

    camera = await client.game_client.free_camera_controller()
    for action in new_commands:
        await parse_camera_command(camera, action)


async def parse_camera_command(camera: CameraController, command_str: str):
    command_str = command_str.replace(', ', ',')
    command_str = command_str.replace('_', '')
    split_command = tokenize(command_str)

    if not split_command:
        return 

    origin_pos = await camera.position()
    origin_orientation = await camera.orientation()
    xyzs, orientations = await parse_location(split_command, camera)

    if split_command[-1].isdigit():
        time = float(split_command[-1])

    else:
        time = 0

    match split_command[0].lower():
        case 'glideto':
            if len(xyzs) >= 2:
                logger.debug(f'Gliding freecam from {origin_pos} to {handle_index(xyzs)} while looking at {handle_index(xyzs, 1)} over {time} seconds')

            else:
                logger.debug(f'Gliding freecam from {origin_pos} to {handle_index(xyzs)} while orientated as {handle_index(orientations)} over {time} seconds')

            await glide_to(camera, origin_pos, handle_index(xyzs), handle_index(orientations, default=origin_orientation), time, handle_index(xyzs, 1))

        case 'rotatingglideto':
            logger.debug(f'Gliding freecam from {origin_pos} to {handle_index(xyzs)} while rotating {handle_index(orientations)} degrees over {time} seconds')
            await rotating_glide_to(camera, origin_pos, handle_index(xyzs), time, handle_index(orientations))

        case 'orbit':
            degrees = param_input(split_command[-2], 360)
            logger.debug(f'Orbiting freecam {degrees} degrees from {origin_pos} around {handle_index(xyzs)} over {time} seconds')
            await orbit(camera, origin_pos, handle_index(xyzs), degrees, time)

        case 'lookat':
            logger.debug(f'Pointing freecam at {handle_index(xyzs)}')
            await point_to_xyz(camera, handle_index(xyzs))

        case 'setpos':
            logger.debug(f'Moving freecam to {handle_index(xyzs)}')
            await camera.write_position(xyzs[0])

        case 'setorient':
            await camera.update_orientation(handle_index(orientations))

        case _:
            pass
