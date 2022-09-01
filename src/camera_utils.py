import asyncio
import math
from time import perf_counter
from typing import List
from wizwalker import XYZ, Client
from wizwalker.memory.memory_objects.camera_controller import CameraController
from src.teleport_math import calculate_yaw, calculate_pitch, calc_multiplerPointOn3DLine, rotate_point
from src.sprinty_client import SprintyClient
from src.types import Orientation


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


async def measure_interval(camera: CameraController, iterations: int = 1000, xyz: bool = True, orientation: bool = True) -> float:
    xyz = await camera.position()
    ypr = await get_camera_orientation(camera)

    times: List[float] = []
    for _ in range(iterations):
        start = perf_counter()

        if xyz:
            await camera.write_position(xyz)

        if orientation:
            await write_camera_orientation(camera, ypr)

        end = perf_counter()

        times.append(end - start)

    return sum(times) / len(times)


async def write_camera_orientation(camera: CameraController, orientation: Orientation, update: bool = True):
    # Writes the orientation of the camera controller, then updates the orientation matrix.
    await camera.write_yaw(orientation.yaw)
    await camera.write_pitch(orientation.pitch)
    await camera.write_roll(orientation.roll)

    if update:
        await camera.update_orientation()


async def get_camera_orientation(camera: CameraController) -> Orientation:
    yaw = await camera.yaw()
    pitch = await camera.pitch()
    roll = await camera.roll()

    return Orientation(yaw, pitch, roll)


# async def glide_to(camera: CameraController, xyz_1: XYZ, xyz_2: XYZ, orientation: Orientation, time: float, focus_xyz: XYZ = None, interval: float = 0.00015):
#     cam_path: List[XYZ] = []

#     for i in range(int(time / interval)):
#         path_xyz = calc_multiplerPointOn3DLine(xyz_1, xyz_2, i / (time / interval))
#         cam_path.append(path_xyz)

#     roll = await camera.roll()

#     for xyz in cam_path:
#         if focus_xyz:
#             yaw = calculate_yaw(xyz, focus_xyz)
#             pitch = calculate_pitch(xyz, focus_xyz)

#             await camera.write_position(xyz)
#             await write_camera_orientation(camera, Orientation(yaw, pitch, roll))

#         else:
#             await camera.write_position(xyz, orientation)

#         await asyncio.sleep(0)


async def glide_to(camera: CameraController, xyz_1: XYZ, xyz_2: XYZ, orientation: Orientation, ttime: float, focus_xyz: XYZ = None):
    roll = await camera.roll()

    velocity = XYZ(
        (xyz_2.x - xyz_1.x) / ttime,
        (xyz_2.y - xyz_1.y) / ttime,
        (xyz_2.z - xyz_1.z) / ttime,
    )

    cur_xyz = xyz_1
    await camera.write_position(cur_xyz)

    start_time = perf_counter()
    prev_time = start_time
    while perf_counter() - start_time < ttime:
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
            await write_camera_orientation(camera, Orientation(yaw, pitch, roll))
        else:
            await write_camera_orientation(camera, orientation)

        await camera.write_position(cur_xyz)

        await asyncio.sleep(0)


async def rotating_glide_to(camera: CameraController, xyz_1: XYZ, xyz_2: XYZ, time: float, degrees: Orientation = Orientation(0, 0, 0), interval: float = 0.00015):
    cam_path: List[XYZ] = []
    iterations = int(time / interval)

    for i in range(iterations):
        path_xyz = calc_multiplerPointOn3DLine(xyz_1, xyz_2, i / (time / interval))
        cam_path.append(path_xyz)

    degrees_intervals = Orientation(math.radians(degrees.yaw / iterations), math.radians(degrees.pitch / iterations), math.radians(degrees.roll / iterations))

    yaw = await camera.yaw()
    pitch = await camera.pitch()
    roll = await camera.roll()

    for xyz in cam_path:
        yaw += degrees_intervals.yaw
        pitch += degrees_intervals.pitch
        roll += degrees_intervals.roll

        await camera.write_position(xyz)
        await write_camera_orientation(camera, Orientation(yaw, pitch, roll))

        await asyncio.sleep(0)


async def orbit(camera: CameraController, xyz_1: XYZ, xyz_2: XYZ, degrees: float, time: float, interval: float = 0.00015):
    cam_path: List[XYZ] = []

    for i in range(int(time / interval)):
        path_xyz = rotate_point(xyz_2, xyz_1, (i / (time / interval)) * degrees)
        cam_path.append(path_xyz)

    roll = await camera.roll()

    for xyz in cam_path:
        yaw = calculate_yaw(xyz, xyz_2)
        pitch = calculate_pitch(xyz, xyz_2)

        await camera.write_position(xyz)
        await write_camera_orientation(camera, Orientation(yaw, pitch, roll))

        await asyncio.sleep(0)