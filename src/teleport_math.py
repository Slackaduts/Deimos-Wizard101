import asyncio
from wizwalker import XYZ, Orient, Client, Keycode
from wizwalker.file_readers.wad import Wad
import math
import struct
from io import BytesIO
from typing import Tuple, Union
from src.utils import is_free
from copy import copy

type_format_dict = {
"char": "<c",
"signed char": "<b",
"unsigned char": "<B",
"bool": "?",
"short": "<h",
"unsigned short": "<H",
"int": "<i",
"unsigned int": "<I",
"long": "<l",
"unsigned long": "<L",
"long long": "<q",
"unsigned long long": "<Q",
"float": "<f",
"double": "<d",
}



class TypedBytes(BytesIO):
    def split(self, index: int) -> Tuple["TypedBytes", "TypedBytes"]:
        self.seek(0)
        buffer = self.read(index)
        return type(self)(buffer), type(self)(self.read())
    def read_typed(self, type_name: str):
        type_format = type_format_dict[type_name]
        size = struct.calcsize(type_format)
        data = self.read(size)
        return struct.unpack(type_format, data)[0]



# implemented from https://github.com/PeechezNCreem/navwiz/
# this licence covers the below function
# Boost Software License - Version 1.0 - August 17th, 2003
#
# Permission is hereby granted, free of charge, to any person or organization
# obtaining a copy of the software and accompanying documentation covered by
# this license (the "Software") to use, reproduce, display, distribute,
# execute, and transmit the Software, and to prepare derivative works of the
# Software, and to permit third-parties to whom the Software is furnished to
# do so, all subject to the following:
#
# The copyright notices in the Software and this entire statement, including
# the above license grant, this restriction and the following disclaimer,
# must be included in all copies of the Software, in whole or in part, and
# all derivative works of the Software, unless such copies or derivative
# works are solely in the form of machine-executable object code generated by
# a source language processor.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE, TITLE AND NON-INFRINGEMENT. IN NO EVENT
# SHALL THE COPYRIGHT HOLDERS OR ANYONE DISTRIBUTING THE SOFTWARE BE LIABLE
# FOR ANY DAMAGES OR OTHER LIABILITY, WHETHER IN CONTRACT, TORT OR OTHERWISE,
# ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.

def parse_nav_data(file_data: Union[bytes, TypedBytes]):
    # ty starrfox for remaking this
    if isinstance(file_data, bytes):
        file_data = TypedBytes(file_data)
    vertex_count = file_data.read_typed("short")
    vertex_max = file_data.read_typed("short")
    # unknown bytes
    file_data.read_typed("short")
    vertices = []
    idx = 0
    while idx <= vertex_max - 1:
        x = file_data.read_typed("float")
        y = file_data.read_typed("float")
        z = file_data.read_typed("float")
        vertices.append(XYZ(x, y, z))
        vertex_index = file_data.read_typed("short")
        if vertex_index != idx:
            vertices.pop()
            vertex_max -= 1
        else:
            idx += 1
    edge_count = file_data.read_typed("int")
    edges = []
    for idx in range(edge_count):
        start = file_data.read_typed("short")
        stop = file_data.read_typed("short")
        edges.append((start, stop))
    return vertices, edges

def get_neighbors(vertex: XYZ, vertices: list[XYZ], edges: list[(int, int)]):
    vert_idx = -1
    for v in vertices:
        vert_idx += 1
        if v == vertex:
            break
    if vert_idx == -1:
        # no matching index found, return empty
        return []

    result = []
    for edge in edges:
        if edge[0] == vert_idx:
            result.append(vertices[edge[1]])
    return result


def calc_PointOn3DLine(xyz_1 : XYZ, xyz_2 : XYZ, additional_distance):
    # extends a point on the line created by 2 XYZs by additional_distance. xyz_1 is the origin.
    distance = calc_Distance(xyz_1, xyz_2)
    # distance = math.sqrt((pow(xyz_1.x - xyz_2.x, 2.0)) + (pow(xyz_1.y - xyz_2.y, 2.0)) + (pow(xyz_1.z - xyz_2.z, 2.0)))
    # Doing a rough distance check here since XYZ's aren't always equal even if they have seemingly the same values
    if distance < 1.0:
        return xyz_1
    else:
        n = ((distance - additional_distance) / distance)
        return XYZ(x=((xyz_2.x - xyz_1.x) * n) + xyz_1.x, y=((xyz_2.y - xyz_1.y) * n) + xyz_1.y, z=((xyz_2.z - xyz_1.z) * n) + xyz_1.z)


def are_xyzs_within_threshold(xyz_1 : XYZ, xyz_2 : XYZ, threshold : int = 200):
    # checks if 2 xyz's are within a rough distance threshold of each other. Not actual distance checking, but precision isn't needed for this, this exists to eliminate tiny variations in XYZ when being sent back from a failed port.
    threshold_check = [abs(abs(xyz_1.x) - abs(xyz_2.x)) < threshold, abs(abs(xyz_1.y) - abs(xyz_2.y)) < threshold, abs(abs(xyz_1.z) - abs(xyz_2.z)) < threshold]
    return all(threshold_check)


def calc_squareDistance(xyz_1 : XYZ, xyz_2 : XYZ):
    # calculates the distance between 2 XYZs, but doesn't square root the answer to be much more efficient. Useful for comparing distances, not much else.
    return (pow(xyz_1.x - xyz_2.x, 2.0)) + (pow(xyz_1.y - xyz_2.y, 2.0)) + (pow(xyz_1.z - xyz_2.z, 2.0))


def calc_Distance(xyz_1 : XYZ, xyz_2 : XYZ):
    # calculates the distance between 2 XYZs
    return math.sqrt(calc_squareDistance(xyz_1, xyz_2))


async def calc_FrontalVector(client: Client, xyz : XYZ = None, yaw : float = None, speed_constant : int = 580, speed_adjusted : bool = True, length_adjusted : bool = True):
    # handle if it is adjusted via speed multiplier or just uses the set constant
    if speed_adjusted:
        current_speed = await client.client_object.speed_multiplier()
    else:
        current_speed = 0

    # handles optional xyz param, will default to using the position of the client
    if not xyz:
        xyz = await client.body.position()

    # handles optional yaw paraam, will default to using the yaw of the client
    if not yaw:
        yaw = await client.body.yaw()
    else:
        yaw = yaw

    # adjust the speed constant based on the speed multiplier
    additional_distance = speed_constant * ((current_speed / 100) + 1)

    # calculate point "in front" of XYZ/client using yaw
    frontal_x = (xyz.x - (additional_distance * math.sin(yaw)))
    frontal_y = (xyz.y - (additional_distance * math.cos(yaw)))
    frontal_xyz = XYZ(x=frontal_x, y=frontal_y, z=xyz.z)

    # make a length adjustment since diagonal movements
    if length_adjusted:
        distance = calc_Distance(xyz, frontal_xyz)
        final_xyz = calc_PointOn3DLine(xyz_1=xyz, xyz_2=frontal_xyz, additional_distance=(additional_distance - distance))
    else:
        final_xyz = frontal_xyz

    return final_xyz


# TODO: This has 2 duplicates
async def load_wad(path: str):
    if path is not None:
        return Wad.from_game_data(path.replace("/", "-"))


async def fallback_spiral_tp(client: Client, xyz: XYZ):
    raise NotImplementedError()

async def navmap_tp(client: Client, xyz: XYZ = None, leader_client: Client = None):
    # TODO: What is leader_client meant to be for?
    if not await is_free(client):
        return

    starting_zone = await client.zone_name() # for loading the correct wad and to walk to target as a last resort
    starting_xyz = await client.body.position()
    target_xyz = xyz if xyz is not None else await client.quest_position.position()

    def check_sigma(a: XYZ, b: XYZ, sigma=5.0):
        # check if a distance is more or less zero
        return calc_Distance(a, b) <= sigma

    async def check_success():
        # Check if the teleport succeeded. For this we want to have moved away from the starting position.
        await asyncio.sleep(0.7) # make sure we got useful information
        return not check_sigma(await client.body.position(), starting_xyz)

    async def finished_tp():
        return await check_success() or not await is_free(client) or await client.zone_name() != starting_zone

    if check_sigma(starting_xyz, target_xyz):
        return # save some work

    await client.teleport(target_xyz)
    if await finished_tp():
        return # trivial tp, no point using a more complex method if this one works

    try:
        # attempt to use the nav data
        wad = await load_wad(starting_zone)
        nav_file = await wad.get_file("zone.nav")
        vertices, edges = parse_nav_data(nav_file)
    except:
        # Unable to load nav data. Fall back to primitive spiral pattern
        await fallback_spiral_tp(client, target_xyz)
        return

    # continuation of nav data tp, don't want to swallow potential exceptions in this section
    closest_vertex = vertices[0]
    lowest_distance = calc_Distance(closest_vertex, target_xyz)
    for i in range(1, len(vertices)):
        vertex = vertices[i]
        vert_dist = calc_Distance(vertex, target_xyz)
        if vert_dist < lowest_distance:
            closest_vertex = vertex
            lowest_distance = vert_dist

    max_depth = 3
    queue = [[closest_vertex]]
    relevant = set()
    while len(queue) > 0:
        path = queue.pop()
        v = path[-1]
        relevant.add(v)
        for neighbor in get_neighbors(v, vertices, edges):
            if neighbor in relevant or len(path) + 1 > max_depth:
                continue
            new_path = list(path)
            new_path.append(neighbor)
            queue.append(new_path)

    # average position of the vertices
    avg_xyz = XYZ(0, 0, 0)
    for v in relevant:
        avg_xyz.x += v.x
        avg_xyz.y += v.y
        avg_xyz.z += v.z
    avg_xyz = XYZ(avg_xyz.x / len(relevant), avg_xyz.y / len(relevant), avg_xyz.z / len(relevant))
    # vector from average xyz to target
    av = XYZ(target_xyz.x - avg_xyz.x, target_xyz.y - avg_xyz.y, avg_xyz.z - target_xyz.z)
    # midpoint of line from average point to target
    ap2 = XYZ(avg_xyz.x + av.x / 2, avg_xyz.y + av.y / 2, avg_xyz.z + av.z / 2)
    await client.teleport(ap2)
    if await check_success():
        if await is_free(client) and await client.zone_name() == starting_zone:
            await client.goto(target_xyz.x, target_xyz.y)
        return
    await client.teleport(avg_xyz) # average point
    if await check_success():
        if await is_free(client) and await client.zone_name() == starting_zone:
            await client.goto(target_xyz.x, target_xyz.y)
        return
    await fallback_spiral_tp(client, target_xyz)


def calc_chunks(points: list[XYZ], entity_distance: float = 3147.0) -> list[XYZ]:
    # Returns a list of center points of "chunks" of the map, as defined by the input points.
    min_pos = XYZ(0, 0, 0)
    max_pos = XYZ(0, 0, 0)

    # find the extremes, they act as corners
    for point in points:
        if point.x < min_pos.x:
            min_pos.x = point.x
        if point.y < min_pos.y:
            min_pos.y = point.x

        if point.x > max_pos.x:
            max_pos.x = point.x
        if point.y > max_pos.y:
            max_pos.y = point.y

    # we use an inscribed square for chunking so corners are correctly included, using circles makes dealing with them way more annnoying
    square_side_length = math.sqrt(2) * entity_distance
    half_side_length = square_side_length / 2

    # start half a side length into the base square
    min_pos.x += half_side_length
    min_pos.y += half_side_length
    max_pos.x -= half_side_length
    max_pos.y -= half_side_length

    # must copy because current_point's fields are written to
    current_point = copy(min_pos)
    chunk_points = [min_pos] # current_point handled here as starting point
    leftover_points = set(points)
    # Turning the given points into a grid would be more efficient than this algorithm
    while True:
        # move the center of the rectangle to next rectangle
        current_point.x += square_side_length
        if current_point.x + half_side_length > max_pos.x:
            # next row
            current_point.x = min_pos.x + half_side_length
            current_point.y += square_side_length
            if current_point.y + half_side_length > max_pos.y:
                # scanned until the end
                break

        # filter squares that do not contain any points
        square_top_left = XYZ(current_point.x - half_side_length, current_point.y - half_side_length, 0)
        square_bottom_right = XYZ(current_point.x + half_side_length, current_point.y + half_side_length, 0)
        has_points = False
        contained_points = set(leftover_points)
        for p in leftover_points:
            if p.x >= square_top_left.x and p.x < square_bottom_right.x and p.y >= square_top_left.y and p.y < square_bottom_right.y:
                contained_points.add(p)
                has_points = True
        # a point cannot be in multiple squares at once
        leftover_points = leftover_points - contained_points

        if has_points:
            chunk_points.append(copy(current_point))

    print(f'chunks:{len(chunk_points)}')
    return chunk_points


def calculate_yaw(xyz_1: XYZ, xyz_2: XYZ) -> float:
    # Calculates the yaw between 2 points.
    dx = xyz_1.x - xyz_2.x
    dy = xyz_1.y - xyz_2.y

    return math.atan2(dx, dy)


def calculate_pitch(xyz_1: XYZ, xyz_2: XYZ) -> float:
    # Find the reference vector
    x = xyz_2.x - xyz_1.x
    y = xyz_2.y - xyz_1.y
    z = xyz_2.z - xyz_1.z

    return -math.atan2(z, math.sqrt(x ** 2 + y ** 2))
