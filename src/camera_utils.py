import asyncio
import math
from time import perf_counter
from typing import List
from wizwalker import XYZ, Client
from wizwalker.memory.memory_objects.camera_controller import CameraController
from src.teleport_math import calculate_yaw, calculate_pitch, calc_frontal_XYZ, get_rotations, calc_multiplerPointOn3DLine, YPR, rotate_point, write_ypr
from src.sprinty_client import SprintyClient


async def point_to_xyz(camera: CameraController, xyz: XYZ):
    camera_pos = await camera.position()
    yaw = calculate_yaw(camera_pos, xyz)
    pitch = calculate_pitch(camera_pos, xyz)

    await camera.write_yaw(yaw)
    await camera.write_pitch(pitch)


async def point_to_vague_entity(client: Client, entity_name: str):
    sprinter = SprintyClient(client)
    entity = await sprinter.find_closest_by_vague_name(entity_name)

    entity_pos = await entity.location()
    await client.camera_freecam()
    camera = await client.game_client.free_camera_controller()

    await point_to_xyz(camera, entity_pos)


async def toggle_player_invis(client: Client, default_scale: float = 1.0):
    scale = await client.body.scale()
    if scale:
        await client.body.write_scale(0.0)

    else:
        await client.body.write_scale(default_scale)


async def glide_to(client: Client, xyz_1: XYZ, xyz_2: XYZ, ypr: YPR, time: float, focus_xyz: XYZ = None, interval: float = 0.015):
    tp_path: List[XYZ] = []

    for i in range(int(time / interval)):
        path_xyz = calc_multiplerPointOn3DLine(xyz_1, xyz_2, i / (time / interval))
        tp_path.append(path_xyz)

    await write_ypr(client, ypr)

    for xyz in tp_path:
        if focus_xyz:
            yaw = calculate_yaw(xyz, focus_xyz)
            await client.teleport(xyz, yaw=yaw)

        else:
            await client.teleport(xyz)

        await asyncio.sleep(interval)


async def rotating_glide_to(client: Client, xyz_1: XYZ, xyz_2: XYZ, time: float, degrees: float, interval: float = 0.015):
    await client.body.write_scale(0)
    tp_path: List[XYZ] = []
    iterations = int(time / interval)

    for i in range(iterations):
        path_xyz = calc_multiplerPointOn3DLine(xyz_1, xyz_2, i / (time / interval))
        tp_path.append(path_xyz)

    degrees_interval = degrees / iterations

    for xyz in tp_path:
        yaw = await client.body.yaw()
        new_yaw = yaw + math.radians(degrees_interval)

        await client.teleport(xyz, yaw = new_yaw)

        await asyncio.sleep(interval)


async def orbit(client: Client, xyz_1: XYZ, xyz_2: XYZ, degrees: float, time: float, interval: float = 0.015):
    tp_path: List[XYZ] = []

    for i in range(int(time / interval)):
        path_xyz = rotate_point(xyz_2, xyz_1, (i / (time / interval)) * degrees)
        tp_path.append(path_xyz)

    for xyz in tp_path:
        yaw = calculate_yaw(xyz, xyz_2)
        pitch = calculate_pitch(xyz, xyz_2)
        
        await client.teleport(xyz, yaw=yaw)
        await client.body.write_pitch(pitch)
        await asyncio.sleep(interval)


async def freecam_forward(client: Client, distance: float, yaw: float = None):
    xyz = await client.body.position()
    ypr = await get_rotations(client)

    destination = await calc_frontal_XYZ(xyz, ypr, distance)






