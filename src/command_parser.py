import traceback
from asyncio import CancelledError
from typing import List, Tuple, Coroutine
import asyncio
from wizwalker import Client, XYZ, Orient, Keycode
from wizwalker.errors import HookNotActive
from wizwalker.extensions.wizsprinter.wiz_navigator import toZone
from wizwalker.memory.memory_objects.camera_controller import CameraController

from src.sprinty_client import SprintyClient
from src.gui_inputs import is_numeric, param_input
from src.utils import index_with_str, get_window_from_path, teleport_to_friend_from_list, auto_potions_force_buy, use_potion, is_free, logout_and_in, click_window_by_path, attempt_activate_mouseless, attempt_deactivate_mouseless, wait_for_visible_by_path, refill_potions, refill_potions_if_needed
from src.camera_utils import glide_to, point_to_xyz, rotating_glide_to, orbit
import re
from loguru import logger


async def parse_location(commands: List[str], camera: CameraController = None, client: Client = None) -> Tuple[XYZ, Orient]:
    # Takes in a camera or client along with a command string, and returns the location. Uses the same input parsing the GUI does, allowing for equation support.
    xyz = XYZ
    orientation: Orient

    location: List[str] = [s.replace(')', '').lower() for s in commands]

    if camera:
        default_xyz = await camera.position()
        default_orientation = await camera.orientation()

    else:
        default_xyz = await client.body.position()
        default_orientation = await client.body.orientation()

    xyz_index = index_with_str(location, 'xyz(')
    if xyz_index is not None:
        xyz = XYZ(
            param_input(location[xyz_index].replace('xyz(', ''), default_xyz.x), 
            param_input(location[xyz_index + 1], default_xyz.y), 
            param_input(location[xyz_index + 2], default_xyz.z)
            )

    else:
        xyz = default_xyz
    orientation_index = index_with_str(location, 'orient(')
    if orientation_index is not None:
        orientation = Orient(
            param_input(location[orientation_index].replace('orient(', ''), default_orientation.pitch), 
            param_input(location[orientation_index + 1], default_orientation.roll), 
            param_input(location[orientation_index + 2], default_orientation.yaw)
            )

    else:
        orientation = default_orientation
    return (xyz, orientation)


def client_from_titles(clients: List[Client], title_str: str = 'p1') -> Client:
    return [client for client in clients if client.title.lower() == title_str][0]


async def wait_for_coro(coro: Coroutine, wait_for_not: bool = False, interval: float = 0.25):
    if wait_for_not:
        while await coro():
            await asyncio.sleep(interval)

    else:
        while not await coro():
            await asyncio.sleep(interval)


def find_path(commands: List[str], starting_index: int = 2) -> List[str]:
    relevant_strings: List[str] = commands[starting_index:]
    path_str: str = re.findall('\[(.*?)\]|$', ','.join(relevant_strings))[0]
    desired_path: List[str] = path_str.strip('[]"').replace("'", "").split(',')

    return desired_path


def split_line(input_str: str, seperator: str = ',') -> List[str]:
    input_str = input_str.replace(f'{seperator} ', seperator)
    split_str = input_str.split(seperator)

    return split_str


async def parse_locations(clients: List[Client], commands: List[str]) -> List[XYZ]:
    xyzs = []
    for client in clients:
        pos, _ = await parse_location(commands, client=client)
        xyzs.append(pos)

    return xyzs


async def parse_command(clients: List[Client], command_str: str):
    all_clients = clients.copy()
    command_str = command_str.replace(', ', ',')

    if 'tozone' not in command_str and 'to_zone' not in command_str:
        command_str = command_str.replace('_', '')

    split_command = split_line(command_str)

    match split_command[0].lower():
        case 'kill' | 'killbot' | 'stop' | 'stopbot' | 'end' | 'exit':
            # Kills the bot loop, useful for not having stuff loop
            raise CancelledError

        case 'sleep' | 'wait' | 'delay':
            # Delays a specified number of seconds
            await asyncio.sleep(float(split_command[-1]))

        case 'log' | 'debug' | 'print':
            # Logs a specific message or prints the text of a window (by path, if any)
            if split_command[1].lower() != 'window':
                relevant_string: str = ' '.join(split_command[1:])
                logger.debug(relevant_string)

            else:
                desired_path = find_path(split_command)
                for client in clients:
                    desired_window = await get_window_from_path(client.root_window, desired_path)
                    relevant_string = await desired_window.maybe_text()
                    logger.debug(relevant_string)

        case _:
            client_str = split_command[0].replace(' ', '')
            exclude = False
            if 'except' in client_str:
                client_str = client_str.replace('except', '')
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
                                xyzs = await parse_locations(clients, split_command)
                                await asyncio.gather(*[client.teleport(xyz) for client, xyz in zip(clients, xyzs)])

                case 'walkto' | 'goto':
                    # Walks in a straight line to a given XYZ (Z agnostic)
                    xyzs = await parse_locations(clients, split_command)
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

                case 'waitforzonechange':
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
                    await asyncio.gather(*[attempt_activate_mouseless(client) for client in clients])
                    await asyncio.gather(*[client.mouse_handler.click(int(split_command[2], int(split_command[3]))) for client in clients])
                    await asyncio.gather(*[attempt_deactivate_mouseless(client) for client in clients])

                case 'clickwindow':
                    # Clicks a specific window by path
                    desired_path = find_path(split_command)
                    await asyncio.gather(*[click_window_by_path(client, desired_path, True) for client in clients])

                case 'waitforwindow' | 'waitforpath':
                    # Waits for a specific window (by path) to be visible
                    desired_path = find_path(split_command)
                    await asyncio.gather(*[wait_for_visible_by_path(client, desired_path) for client in clients])
                    if split_command[-1].lower() == 'completion':
                        # Waits for a specific window (by path) to not be visible
                        await asyncio.gather(*[wait_for_visible_by_path(client, desired_path, True) for client in clients])

                case 'friendtp' | 'friendteleport':
                    # Teleports specified clients to another via wizard name or icon
                    await asyncio.gather(*[client.mouse_handler.activate_mouseless() for client in clients])
                    await asyncio.sleep(.25)

                    if split_command[2] == 'icon':
                        await asyncio.gather(*[teleport_to_friend_from_list(client, icon_list=2, icon_index=0) for client in clients])
                    else:
                        await asyncio.gather(*[teleport_to_friend_from_list(client, name=split_command[2]) for client in clients])

                    await asyncio.gather(*[client.mouse_handler.deactivate_mouseless() for client in clients])

                case 'entitytp' | 'entityteleport':
                    # Teleports to a specific entity by vague name
                    await asyncio.gather(*[SprintyClient(client).tp_to_closest_by_vague_name(split_command[2]) for client in clients])

                case 'tozone' | 'to_zone':
                    # Navigates to a specific zone, by vague name
                    await toZone(clients, split_command[2])

                case _:
                    await asyncio.sleep(0.25)

    await asyncio.sleep(0)


async def execute_flythrough(client: Client, flythrough_data: str, line_seperator: str = '\n'):
    flythrough_actions = flythrough_data.split(line_seperator)

    if not await client.game_client.is_freecam():
        await client.camera_freecam()

    camera = await client.game_client.free_camera_controller()
    for action in flythrough_actions:
        await parse_camera_command(camera, action)


async def parse_camera_command(camera: CameraController, command_str: str):
    command_str = command_str.replace(', ', ',')
    command_str = command_str.replace('_', '')
    split_command = split_line(command_str)

    origin_pos = await camera.position()
    xyz, orientation = await parse_location(split_command, camera)
    focus_xyz: XYZ = None

    if split_command[-1].isdigit():
        time = float(split_command[-1])

    else:
        time = 0

    match split_command[0].lower():
        case 'glideto':
            focus_index = index_with_str(split_command, 'lookat')
            if focus_index is not None:
                focus_xyz, _ = await parse_location(split_command[focus_index:-1], camera)
                logger.debug(f'Gliding freecam from {origin_pos} to {xyz} while looking at {focus_xyz} over {time} seconds')

            else:
                logger.debug(f'Gliding freecam from {origin_pos} to {xyz} while orientated as {orientation} over {time} seconds')

            await glide_to(camera, origin_pos, xyz, orientation, time, focus_xyz)

        case 'rotatingglideto':
            logger.debug(f'Gliding freecam from {origin_pos} to {xyz} while rotating {orientation} degrees over {time} seconds')
            await rotating_glide_to(camera, origin_pos, xyz, time, orientation)

        case 'orbit':
            degrees = param_input(split_command[-2], 360)
            logger.debug(f'Orbiting freecam {degrees} degrees from {origin_pos} around {xyz} over {time} seconds')
            await orbit(camera, origin_pos, xyz, degrees, time)

        case 'lookat':
            logger.debug(f'Pointing freecam at {xyz}')
            await point_to_xyz(camera, xyz)

        case 'setpos':
            logger.debug(f'Moving freecam to {xyz}')
            await camera.write_position(xyz)

        case 'setorient':
            await camera.update_orientation(orientation)

        case _:
            pass
