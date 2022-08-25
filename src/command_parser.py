from typing import List, Tuple, Coroutine
import asyncio
from wizwalker import Client, XYZ
from src.gui_inputs import param_input
from src.utils import use_potion, buy_potions
from src.teleport_math import YPR 



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
    split_location = location_str.split(' ')
    location_type = split_location.pop(0)
    location = list(map(float, split_location))

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


async def parse_command(client: Client, clients: List[Client], commands: str):
    split_command = commands.split(' ')
    if split_command[-1].lower() == 'mass':
        mass = True

    else:
        mass = False


    match split_command[0].lower():
        case 'freecam':
            await client.camera_swap() if mass else await asyncio.gather(*[client.camera_swap() for client in clients])

        case 'use_potion':
            await use_potion(client) if mass else await asyncio.gather(*[use_potion(client) for client in clients])

        case 'buy_potions':
            await buy_potions(client) if mass else await asyncio.gather(*[buy_potions(client) for client in clients])

        case 'speed':
            default_speed = await client.client_object.speed_multiplier()
            await client.client_object.write_speed_multiplier(parse_number(split_command[1], default_speed)) if mass else await asyncio.gather(*[client.client_object.write_speed_multiplier(parse_number(split_command[1], default_speed)) for client in clients])

        case 'teleport':
            xyz, ypr = await parse_location(client, split_command[1])

