from typing import List, Tuple, Coroutine
import asyncio
from wizwalker import Client, XYZ, Keycode
from wizwalker.memory.memory_objects.camera_controller import CameraController
from src.gui_inputs import param_input
from src.utils import use_potion, buy_potions, is_free, logout_and_in, wait_for_visible_by_path, click_window_by_path, attempt_activate_mouseless, attempt_deactivate_mouseless
from src.teleport_math import get_orientation, navmap_tp, write_orientation
from src.camera_utils import get_camera_orientation, glide_to, point_to_xyz, rotating_glide_to, orbit, write_camera_orientation, measure_interval
from src.types import Orientation
import re
from loguru import logger


def index_with_str(input: List[str], desired_str: str) -> int:
    for i, s in enumerate(input):
        if desired_str in s.lower():
            return i

    return None


async def parse_location(commands: List[str], camera: CameraController = None, client: Client = None) -> Tuple[XYZ, Orientation]:
    # Takes in a camera or client along with a command string, and returns the location. Uses the same input parsing the GUI does, allowing for equation support.
    xyz = XYZ
    orientation = Orientation

    location: List[str] = [s.replace(')', '').lower() for s in commands]

    if camera:
        default_xyz = await camera.position()
        default_orientation = await get_camera_orientation(camera)

    else:
        default_xyz = await client.body.position()
        default_orientation = await get_orientation(client)

    xyz_index = index_with_str(location, 'xyz(')
    if xyz_index is not None:
        xyz = XYZ(
            param_input(location[xyz_index].replace('xyz(', ''), default_xyz.x), 
            param_input(location[xyz_index + 1], default_xyz.y), 
            param_input(location[xyz_index + 2], default_xyz.z)
            )

    else:
        xyz = default_xyz
    orientation_index = index_with_str(location, 'orientation(')
    if orientation_index is not None:
        orientation = Orientation(
            param_input(location[orientation_index].replace('orientation(', ''), default_orientation.yaw), 
            param_input(location[orientation_index + 1], default_orientation.pitch), 
            param_input(location[orientation_index + 2], default_orientation.roll)
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


def find_path(input_str: str) -> List[str]:
    path_str: str = re.findall('(?<=\[).+?(?=\])', input_str)[0]
    path_str = path_str.replace(' ', '')
    window_path = path_str.split(',')

    return window_path


def split_line(input_str: str, seperator: str = ',') -> List[str]:
    input_str = input_str.replace(f'{seperator} ', seperator)
    split_str = input_str.split(seperator)

    return split_str


async def parse_command(clients: List[Client], command_str: str):
    command_str = command_str.replace(', ', ',')
    command_str = command_str.replace('_', '')
    split_command = split_line(command_str)

    # Get the desired client, will default to p1 if mass or no client is specified
    client_str = split_command[0]
    mass = client_str == 'mass'
    if client_str[1:].isdigit() and not mass:
        desired_client = client_from_titles(clients, client_str)
        mass = False

    else:
        desired_client = clients[0]

    match split_command[1].lower():
        case 'teleport' | 'tp':
            xyz, _ = await parse_location(split_command, client=desired_client)
            await desired_client.teleport(xyz) if not mass else await asyncio.gather(*[client.teleport(xyz) for client in clients])

        case 'navmapteleport | navmaptp':
            xyz, _ = await parse_location(split_command, client=desired_client)
            await navmap_tp(desired_client, xyz) if not mass else await asyncio.gather(*[navmap_tp(client, xyz) for client in clients])

        case 'walkto' | 'goto':
            xyz, _ = await parse_location(split_command, client=desired_client)
            await desired_client.goto(xyz.x, xyz.y) if not mass else await asyncio.gather(*[client.goto(xyz.x, xyz.y) for client in clients])

        case 'sendkey' | 'press' | 'presskey':
            key = split_command[2]
            time = 0.1
            if len(split_command) >= 4:
                time = float(split_command[3])

            await desired_client.send_key(Keycode[key], time)

        case 'waitfordialog' | 'waitfordialogue':
            await wait_for_coro(desired_client.is_in_dialog) if not mass else await asyncio.gather(*[wait_for_coro(client.is_in_dialog) for client in clients])

            if split_command[1].lower() == 'completion':
                await wait_for_coro(desired_client.is_in_dialog, True) if not mass else await asyncio.gather(*[wait_for_coro(client.is_in_dialog, True) for client in clients])

        case 'waitforbattle' | 'waitforcombat':
            await wait_for_coro(desired_client.in_battle) if not mass else await asyncio.gather(*[wait_for_coro(client.in_battle) for client in clients])

            if split_command[-1].lower() == 'completion':
                await wait_for_coro(desired_client.in_battle, True) if not mass else await asyncio.gather(*[wait_for_coro(client.in_battle, True) for client in clients])

        case 'waitforzonechange':
            await desired_client.wait_for_zone_change() if not mass else await asyncio.gather(*[client.wait_for_zone_change() for client in clients])

            if split_command[-1].lower() == 'completion':
                await wait_for_coro(desired_client.is_loading) if not mass else await asyncio.gather(*[wait_for_coro(client.is_loading) for client in clients])

        case 'waitforfree':
            async def _wait_for_free(client: Client, wait_for_not: bool = False, interval: float = 0.25):
                if wait_for_not:
                    while await is_free(client):
                        await asyncio.sleep(interval)

                else:
                    while not await is_free(client):
                        await asyncio.sleep(interval)

            await _wait_for_free(desired_client) if not mass else await asyncio.gather(*[_wait_for_free(client) for client in clients])

            if split_command[1].lower() == 'completion':
                await _wait_for_free(desired_client, True) if not mass else await asyncio.gather(*[_wait_for_free(client, True) for client in clients])

        case 'usepotion':
            await use_potion(desired_client) if not mass else await asyncio.gather(*[use_potion(client) for client in clients])

        case 'buypotions':
            await buy_potions(desired_client) if not mass else await asyncio.gather(*[buy_potions(client) for client in clients])

        case 'speed':
            await desired_client.client_object.write_speed_multiplier(int(split_command[-1])) if not mass else await asyncio.gather(*[client.client_object.write_speed_multiplier(int(split_command[-1])) for client in clients])

        case 'sleep' | 'wait' | 'delay':
            await asyncio.sleep(float(split_command[-1]))

        case 'logoutandin' | 'relog':
            await logout_and_in(desired_client) if not mass else await asyncio.gather(*[logout_and_in(client) for client in clients])

        case _:
            await asyncio.sleep(0.25)


async def execute_flythrough(client: Client, flythrough_data: str, line_seperator: str = '\n'):
    flythrough_actions = flythrough_data.split(line_seperator)

    if not await client.game_client.is_freecam():
        await client.camera_freecam()

    camera = await client.game_client.free_camera_controller()

    for action in flythrough_actions:
        await parse_camera_command(camera, action)


async def parse_camera_command(camera: CameraController, command_str: str):
    command_str = command_str.replace(', ', ',')
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

        case 'setorientation':
            await write_camera_orientation(camera, orientation)

        case _:
            pass
