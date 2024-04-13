import asyncio
import math
from time import perf_counter
from typing import List
from wizwalker import XYZ, Orient, Client
from wizwalker.memory.memory_objects.camera_controller import CameraController
from src.teleport_math import calculate_yaw, calculate_pitch
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


async def glide_to(camera: CameraController, xyz_1: XYZ, xyz_2: XYZ, orientation: Orient, time: float, focus_xyz: XYZ = None):
    pitch, roll, yaw = orientation
    roll = await camera.roll()

    velocity = XYZ(
        (xyz_2.x - xyz_1.x) / time,
        (xyz_2.y - xyz_1.y) / time,
        (xyz_2.z - xyz_1.z) / time,
    )

    cur_xyz = xyz_1
    await camera.write_position(cur_xyz)

    start_time = perf_counter()
    prev_time = start_time
    while perf_counter() - start_time < time:
        now = perf_counter()
        dt = now - prev_time
        prev_time = now

        cur_xyz = XYZ(
            cur_xyz.x + (velocity.x * dt),
            cur_xyz.y + (velocity.y * dt),
            cur_xyz.z + (velocity.z * dt),
        )

        if focus_xyz:
            yaw = calculate_yaw(cur_xyz, focus_xyz)
            pitch = calculate_pitch(cur_xyz, focus_xyz)
            await camera.update_orientation(Orient(pitch, roll, yaw))
        else:
            await camera.update_orientation(Orient(pitch, roll, yaw))

        await camera.write_position(cur_xyz)

        await asyncio.sleep(0)


async def rotating_glide_to(camera: CameraController, xyz_1: XYZ, xyz_2: XYZ, time: float, degrees = Orient(0, 0, 0)):
    rotation_velocity = Orient(
        math.radians(degrees.pitch) / time,
        math.radians(degrees.roll) / time,
        math.radians(degrees.yaw) / time,
    )

    pitch, roll, yaw = await camera.orientation()

    velocity = XYZ(
        (xyz_2.x - xyz_1.x) / time,
        (xyz_2.y - xyz_1.y) / time,
        (xyz_2.z - xyz_1.z) / time,
    )

    cur_xyz = xyz_1
    await camera.write_position(cur_xyz)

    start_time = perf_counter()
    prev_time = start_time
    while perf_counter() - start_time < time:
        now = perf_counter()
        dt = now - prev_time
        prev_time = now

        cur_xyz = XYZ(
            cur_xyz.x + (velocity.x * dt),
            cur_xyz.y + (velocity.y * dt),
            cur_xyz.z + (velocity.z * dt),
        )

        yaw += rotation_velocity.yaw * dt
        pitch += rotation_velocity.pitch * dt
        roll += rotation_velocity.roll * dt

        await camera.write_position(cur_xyz)
        await camera.update_orientation(Orient(pitch, roll, yaw))

        await asyncio.sleep(0)


async def orbit(camera: CameraController, xyz_1: XYZ, xyz_2: XYZ, degrees: float, time: float):
    roll = await camera.roll()

    xy_radius = math.sqrt((xyz_2.x - xyz_1.x) ** 2 + (xyz_2.y - xyz_1.y) ** 2)

    angle_velocity = math.radians(degrees) / time
    cur_angle = math.atan2((xyz_2.y - xyz_1.y), (xyz_2.x - xyz_1.x))

    start_time = perf_counter()
    prev_time = start_time
    while perf_counter() - start_time < time:
        now = perf_counter()
        dt = now - prev_time
        prev_time = now

        cur_angle += angle_velocity * dt

        cur_xyz = XYZ(
            xyz_2.x - xy_radius * math.cos(cur_angle),
            xyz_2.y - xy_radius * math.sin(cur_angle),
            xyz_1.z
        )

        await camera.write_position(cur_xyz)

        yaw = calculate_yaw(cur_xyz, xyz_2)
        pitch = calculate_pitch(cur_xyz, xyz_2)
        await camera.update_orientation(Orient(pitch, roll, yaw))

        await asyncio.sleep(0)
