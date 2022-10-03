from array import ArrayType
import numpy as np
import asyncio
import math
from typing import Iterable, List, Tuple
from wizwalker import XYZ, Orient, Client
import matplotlib
import matplotlib.pyplot as plt
from src.collision import BoxGeomParams, CollisionWorld, CylinderGeomParams, MeshGeomParams, ProxyMesh, ProxyType, SphereGeomParams, TubeGeomParams, get_collision_data, CollisionFlag
from src.teleport_math import calc_squareDistance
import aiofiles
import os

def to_3x3_array(matrix: Iterable) -> ArrayType:
    # Converts an iterable into a 3x3 matrix.
    return np.array([[matrix[0], matrix[1], matrix[2]],
                    [matrix[3], matrix[4], matrix[5]],
                    [matrix[6], matrix[7], matrix[8]]])


def to_1x3_array(matrix: Iterable) -> ArrayType:
    # Converts an iterable into a 1x3 matrix.
    return np.array([matrix[0], matrix[1], matrix[2]])


def cube_to_vertices(l: float, w: float, h: float, position: Iterable, r_matrix: ArrayType) -> List[XYZ]:
    # Converts a cube to its vertices using only its measurements, center position, and a rotation matrix.
    # Divide measurments by 2 as we are starting at the center of the cube
    l /= 2
    w /= 2
    h /= 2

    # Create the 8 vertices of the cube, using every possible combination of adding/subtracting the measurements
    matrices = [
        to_1x3_array((position[0] + w, position[1] + l, position[2] + h)),
        to_1x3_array((position[0] - w, position[1] - l, position[2] - h)),
        to_1x3_array((position[0] + w, position[1] - l, position[2] + h)),
        to_1x3_array((position[0] - w, position[1] + l, position[2] - h)),
        to_1x3_array((position[0] - w, position[1] + l, position[2] + h)),
        to_1x3_array((position[0] + w, position[1] - l, position[2] - h)),
        to_1x3_array((position[0] + w, position[1] + l, position[2] - h)),
        to_1x3_array((position[0] - w, position[1] - l, position[2] + h))
    ]

    # Apply the rotation matrix to every point
    r_matrices = []
    for matrix in matrices:
        d_product = np.dot(matrix, r_matrix)
        r_matrices.append(d_product)

    # Convert every point from a 1x3 array to an XYZ
    points = [XYZ(matrix[0], matrix[1], matrix[2]) for matrix in r_matrices]

    return points


async def plot_cube(client: Client):
    # FOR TESTING - slack
    data = await get_collision_data(client)
    world = CollisionWorld()
    world.load(data)

    points: List[XYZ] = []

    for object in world.objects:
        print(object.category_flags)
        if type(object.params) == BoxGeomParams and object.category_flags == CollisionFlag.OBJECT:
            cube: BoxGeomParams = object.params
            vertices = cube_to_vertices(cube.length, cube.width, cube.depth, object.location, to_3x3_array(object.rotation))
            for xyz in vertices:
                points.append(xyz)

        # elif type(object.params) == CylinderGeomParams:
        #     cylinder: CylinderGeomParams = object.params
        #     vertices = cube_to_vertices(cylinder.radius, cylinder.radius, cylinder.length, object.location, to_3x3_array(object.rotation))
        #     for xyz in vertices:
        #         points.append(xyz)

        # elif type(object.params) == TubeGeomParams:
        #     tube: TubeGeomParams = object.params
        #     vertices = cube_to_vertices(tube.radius, tube.radius, tube.length, object.location, to_3x3_array(object.rotation))
        #     for xyz in vertices:
        #         points.append(xyz)

        # elif type(object.params) == SphereGeomParams:
        #     sphere: SphereGeomParams = object.params
        #     vertices = cube_to_vertices(sphere.radius, sphere.radius, sphere.radius, object.location, to_3x3_array(object.rotation))
        #     for xyz in vertices:
        #         points.append(xyz)

        elif type(object.params) == MeshGeomParams and object.category_flags == CollisionFlag.OBJECT:
            mesh: ProxyMesh = object
            for vertex in mesh.vertices:
                xyz = XYZ(vertex[0], vertex[1], vertex[2])
                points.append(xyz)
    await asyncio.sleep(0)

    player_pos = await client.body.position()

    curr_dist: float = 0.0
    curr_xyz: XYZ = None
    for xyz in points:
        if calc_squareDistance(xyz, player_pos) < curr_dist or not curr_xyz:
            curr_dist = calc_squareDistance(xyz, player_pos)
            curr_xyz = xyz

    print(curr_xyz)
    await client.teleport(curr_xyz)

    if os.path.exists('points.txt'):
        os.remove('points.txt')
        while os.path.exists('points.txt'):
            await asyncio.sleep(0.1)

    with open('points.txt', 'w') as f:
        for xyz in points:
            f.write(f'{xyz.x}, {xyz.y}, {xyz.z}\n')

    print('This finished, for testing purposes')