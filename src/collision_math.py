from array import ArrayType
import numpy as np
import asyncio
import math
from typing import Iterable, List, Tuple, TypeAlias
from wizwalker import XYZ, Orient, Client
# import matplotlib
# import matplotlib.pyplot as plt
from .collision import BoxGeomParams, CollisionWorld, CylinderGeomParams, MeshGeomParams, ProxyMesh, ProxyType, SphereGeomParams, TubeGeomParams, get_collision_data, CollisionFlag
#from teleport_math import calc_squareDistance


# def to_3x3_array(matrix: Iterable) -> ArrayType:
#     # Converts an iterable into a 3x3 matrix.
#     return np.array([[matrix[0], matrix[1], matrix[2]],
#                     [matrix[3], matrix[4], matrix[5]],
#                     [matrix[6], matrix[7], matrix[8]]])


# def to_1x3_array(matrix: Iterable) -> ArrayType:
#     # Converts an iterable into a 1x3 matrix.
#     return np.array([matrix[0], matrix[1], matrix[2]])


# def cube_to_vertices(l: float, w: float, h: float, position: Iterable, r_matrix: ArrayType) -> List[XYZ]:
#     # Converts a cube to its vertices using only its measurements, center position, and a rotation matrix.
#     # Divide measurments by 2 as we are starting at the center of the cube
#     l /= 2
#     w /= 2
#     h /= 2

#     # Create the 8 vertices of the cube, using every possible combination of adding/subtracting the measurements
#     matrices = [
#         to_1x3_array((position[0] + w, position[1] + l, position[2] + h)),
#         to_1x3_array((position[0] - w, position[1] - l, position[2] - h)),
#         to_1x3_array((position[0] + w, position[1] - l, position[2] + h)),
#         to_1x3_array((position[0] - w, position[1] + l, position[2] - h)),
#         to_1x3_array((position[0] - w, position[1] + l, position[2] + h)),
#         to_1x3_array((position[0] + w, position[1] - l, position[2] - h)),
#         to_1x3_array((position[0] + w, position[1] + l, position[2] - h)),
#         to_1x3_array((position[0] - w, position[1] - l, position[2] + h))
#     ]

#     # Apply the rotation matrix to every point
#     r_matrices = []
#     for matrix in matrices:
#         d_product = np.dot(matrix, r_matrix)
#         r_matrices.append(d_product)

#     # Convert every point from a 1x3 array to an XYZ
#     points = [XYZ(matrix[0], matrix[1], matrix[2]) for matrix in matrices]

#     return points


# async def plot_cube(client: Client):
#     # FOR TESTING - slack
#     data = await get_collision_data(client)
#     world = CollisionWorld()
#     world.load(data)

#     points: List[XYZ] = []

#     for object in world.objects:
#         print(object.category_flags)
#         if type(object.params) == BoxGeomParams and object.category_flags == CollisionFlag.OBJECT:
#             cube: BoxGeomParams = object.params
#             vertices = cube_to_vertices(cube.length, cube.width, cube.depth, object.location, to_3x3_array(object.rotation))
#             for xyz in vertices:
#                 points.append(xyz)

#         # elif type(object.params) == CylinderGeomParams:
#         #     cylinder: CylinderGeomParams = object.params
#         #     vertices = cube_to_vertices(cylinder.radius, cylinder.radius, cylinder.length, object.location, to_3x3_array(object.rotation))
#         #     for xyz in vertices:
#         #         points.append(xyz)

#         # elif type(object.params) == TubeGeomParams:
#         #     tube: TubeGeomParams = object.params
#         #     vertices = cube_to_vertices(tube.radius, tube.radius, tube.length, object.location, to_3x3_array(object.rotation))
#         #     for xyz in vertices:
#         #         points.append(xyz)

#         # elif type(object.params) == SphereGeomParams:
#         #     sphere: SphereGeomParams = object.params
#         #     vertices = cube_to_vertices(sphere.radius, sphere.radius, sphere.radius, object.location, to_3x3_array(object.rotation))
#         #     for xyz in vertices:
#         #         points.append(xyz)

#         elif type(object.params) == MeshGeomParams and object.category_flags == CollisionFlag.OBJECT:
#             mesh: ProxyMesh = object
#             for vertex in mesh.vertices:
#                 xyz = XYZ(vertex[0], vertex[1], vertex[2])
#                 points.append(xyz)
#     await asyncio.sleep(0)

#     player_pos = await client.body.position()

#     curr_dist: float = 0.0
#     curr_xyz: XYZ = None
#     for xyz in points:
#         if calc_squareDistance(xyz, player_pos) < curr_dist or not curr_xyz:
#             curr_dist = calc_squareDistance(xyz, player_pos)
#             curr_xyz = xyz

#     print(curr_xyz)
#     await client.teleport(curr_xyz)

#     if os.path.exists('points.txt'):
#         os.remove('points.txt')
#         while os.path.exists('points.txt'):
#             await asyncio.sleep(0.1)

#     with open('points.txt', 'w') as f:
#         for xyz in points:
#             f.write(f'{xyz.x}, {xyz.y}, {xyz.z}\n')

#     print('This finished, for testing purposes')

Matrix3x3: TypeAlias = tuple[
    float, float, float,
    float, float, float,
    float, float, float,
]

def cube_to_xyz(cube:list):
    xyz = []
    for verticies in cube:
        xyz.append(XYZ(verticies[0], verticies[1], verticies[2]))
    return xyz

def find_if_xyz_in_cube(xyz: XYZ, cube: list) -> bool:
    """If True XYZ is in the cube"""
    #https://math.stackexchange.com/questions/1472049/check-if-a-point-is-inside-a-rectangular-shaped-area-3d
    #     7-------6
    #    /|      /|
    #   4-+-----5 | 
    #   | |     | |   y
    #   | 3-----+-2   | z
    #   |/      |/    |/
    #   0-------1     +--x
    
    p0 = XYZ(*cube[0])
    p1 = XYZ(*cube[1])
    p3 = XYZ(*cube[3])
    p4 = XYZ(*cube[4])
    pv = xyz

    i = subtract_xyz(p3, p0)
    j = subtract_xyz(p1, p0)
    k = subtract_xyz(p4, p0)
    v = subtract_xyz(pv, p0)

    if 0 < multiply_xyz(v, i) < multiply_xyz(i, i) and 0 <  multiply_xyz(v, j) < multiply_xyz(j, j) and 0 < multiply_xyz(v, k) < multiply_xyz(k, k):
        return True
    else:
        return False
    
def subtract_xyz(xyz2: XYZ, xyz1: XYZ) -> XYZ:
    # You can perform b - a by doing (bx - ax, by - ay, bz - az).
    return XYZ((xyz2.x - xyz1.x), (xyz2.y - xyz1.y), (xyz2.z - xyz1.z))

def multiply_xyz(a: XYZ, b: XYZ) -> float:
    #a dot b = (ax, ay, az) dot (bx, by, bz) = axbx + ayby + az*bz
    return a.x*b.x + a.y*b.y + a.z*b.z

import random

import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import numpy as np

SimpleFace: TypeAlias = tuple[int, int, int]
SimpleVert: TypeAlias = tuple[float, float, float]
Vector3D: TypeAlias = tuple[float, float, float]

CubeVertices = tuple[Vector3D, Vector3D, Vector3D, Vector3D, Vector3D, Vector3D, Vector3D, Vector3D]


def toCubeVertices(dimensions: Vector3D) -> CubeVertices:
    l, w, d = dimensions
    l /= 2
    w /= 2
    d /= 2
    return (
        (-l, -w, -d),
        (l, -w, -d),
        (l, -w, d),
        (-l, -w, d),

        (-l, w, -d),
        (l, w, -d),
        (l, w, d),
        (-l, w, d),
    )


def toMultidim(mat: Matrix3x3):
    #return (
    #    (mat[0], mat[1], mat[2]),
    #    (mat[3], mat[4], mat[5]),
    #    (mat[6], mat[7], mat[8]),
    #)
    # TODO: Should this be transposed or not? Transposed because the cubes are distorted otherwise
    return (
        (mat[0], mat[3], mat[6]),
        (mat[1], mat[4], mat[7]),
        (mat[2], mat[5], mat[8]),
    )


def transformCube(cube, location, rotation):
    tpoints = [np.dot((p,), toMultidim(rotation))[0] for p in cube]
    for p in tpoints:
        p[0] += location[0]
        p[1] += location[1]
        p[2] += location[2]
    return tpoints


def plotCube(ax, locs, color):
    Z = np.array(locs)
    
    #     7-------6
    #    /|      /|
    #   4-+-----5 | 
    #   | |     | |   y
    #   | 3-----+-2   | z
    #   |/      |/    |/
    #   0-------1     +--x
    verts = [
        [Z[0],Z[1],Z[2],Z[3]],
        [Z[4],Z[5],Z[6],Z[7]],
        [Z[0],Z[1],Z[5],Z[4]],
        [Z[1],Z[2],Z[6],Z[5]],
        [Z[3],Z[2],Z[6],Z[7]],
        [Z[0],Z[3],Z[7],Z[4]],
    ]

    ax.scatter3D(Z[:, 0], Z[:, 1], Z[:, 2])
    ax.add_collection3d(Poly3DCollection(
        verts,
        facecolors=color,
        edgecolors=color,
        alpha=0.5
    ))

#https://stackoverflow.com/questions/21698630/how-can-i-find-if-a-point-lies-inside-or-outside-of-convexhull
def isInHull(P, hull):
    '''
    Datermine if the list of points P lies inside the hull
    :return: list
    List of boolean where true means that the point is inside the convex hull
    '''
    A = hull.equations[:,0:-1]
    b = np.transpose(np.array([hull.equations[:,-1]]))
    isInHull = np.all((A @ np.transpose(P)) <= np.tile(-b,(1,len(P))),axis=0)
    return isInHull


from scipy.spatial import ConvexHull
import matplotlib.pyplot as plt

def cube_collision_check(capsule, cubes: list) -> bool:
    '''checks if a position collides with a cube
    True: Collides
    False: Doesn't collide'''

    for cube in cubes:
        if capsule_in_cube(capsule[0], capsule[1], cube):
            return True
    return False

# from icecream import ic
def cylinder_collision_check(capsule, cylinders: list) -> bool:
    '''checks if a position collides with a cylinder
    True: Collides
    False: Doesn't collide'''

    for cylinder in cylinders:
        if capsule_in_cylinder(capsule, cylinder):
            return True
    return False


def sphere_collision_check(capsule, spheres: list) -> bool:
    '''checks if a position collides with a sphere
    True: Collides
    False: Doesn't collide'''

    for sphere in spheres:
        if capsule_in_sphere(capsule, sphere):
            return True
    return False

def capsule_in_cube(capsule_center,
                capsule_radius,
                cube_vertices
                ):
    # check if capsule center is within cube
    center_within_cube = True
    
    cube_vertices = np.array(cube_vertices)
    
    for i in range(3):
        if not (min(cube_vertices[:,i]) <= capsule_center[i] <= max(cube_vertices[:,i])):
            center_within_cube = False
            break

    if not center_within_cube:
        return False

    # check if capsule radius and height overlap with cube
    closest_distance = float("inf")
    for vertex in cube_vertices:
        distance = np.linalg.norm(vertex - capsule_center)
        if distance < closest_distance:
            closest_distance = distance

    if closest_distance <= capsule_radius:
        return True
    else:
        return False


from icecream import ic
def capsule_in_cylinder(capsule, cylinder):
    capsule_location, capsule_radius, capsule_length  = capsule
    cylinder_location, cylinder_radius, cylinder_length = cylinder
    # calculate the distance between the capsule and cylinder centers
    distance = math.sqrt(
        (capsule_location[0] - cylinder_location[0])**2 +
        (capsule_location[1] - cylinder_location[1])**2 +
        (capsule_location[2] - cylinder_location[2])**2
    )

    # check if the distance is greater than the sum of the radii
    if distance > capsule_radius + cylinder_radius:
        #No overlap
        return False

    # check if the capsule's length plus the cylinder's length is greater than the distance
    if capsule_length + cylinder_length > distance:
        #Partial overlap
        return True

    # if neither of the above conditions are met, then the capsule is fully inside the cylinder
    #Full overlap
    return True

def transformCylinder(location: list, rotation_matrix):
    rotated_location = np.matmul(rotation_matrix, location)
    return rotated_location

from math import sqrt
def capsule_in_sphere(capsule, sphere):
    capsule_loc, capsule_radius, _ = capsule
    sphere_loc, sphere_radius = sphere
    # Calculate the distance between the capsule's center and the sphere's center
    distance = sqrt((capsule_loc[0] - sphere_loc[0]) ** 2 + (capsule_loc[1] - sphere_loc[1]) ** 2 + (capsule_loc[2] - sphere_loc[2]) ** 2)
    # Calculate the sum of the capsule's radius and sphere's radius
    sum_radii = capsule_radius + sphere_radius
    # If the distance between the two centers is less than or equal to the sum of the radii, then there is overlap
    if distance <= sum_radii:
        return True
    else:
        return False


async def testbench():
    from wizwalker import ClientHandler
    #hooks client
    handler = ClientHandler()
    client = handler.get_new_clients()[0]
    await client.activate_hooks()
    print('hooked')
    
    try:
        data = await get_collision_data(client)
        world = CollisionWorld()
        world.load(data)
        # fig = plt.figure()
        # ax = fig.add_subplot(projection="3d")
        cube_list = []
        mesh_list = []
        cylinders_list = []
        sphere_list = []
        from icecream import ic
        for ob in world.objects:
            if ob.proxy == ProxyType.BOX:
                size = (ob.params.length, ob.params.width , ob.params.depth)
                points = toCubeVertices(size)
                cube = transformCube(points, ob.location, ob.rotation)
                cube_list.append(cube)
            elif ob.proxy == ProxyType.CYLINDER:
                #ic(ob.name, ob.rotation)
                # loc = transformCylinder(ob.location, to_3x3_array(ob.rotation))
                # cylinders_list.append((loc, ob.params.radius, ob.params.length))
                # await client.teleport(XYZ(*loc))
                # await asyncio.sleep(3)
                # await client.teleport(XYZ(*ob.location))
                loc = transformCylinder(ob.location, toMultidim(ob.rotation))
                cylinders_list.append((loc, ob.params.radius, ob.params.length))
                print(ob.params.radius)
                #cylinders_list.append((loc, ob.params.radius))
                # await client.teleport(XYZ(*loc))
                # await asyncio.sleep(3)
            elif ob.proxy == ProxyType.SPHERE:
                loc = transformCylinder(ob.location, toMultidim(ob.rotation))
                sphere_list.append((loc, ob.params.radius))

            elif type(ob.params) == MeshGeomParams:
                mesh = transformCube(ob.vertices, ob.location, ob.rotation)
                mesh_list.append(mesh)
            else:
                print(ob.proxy)
        
        meshpoints = []
        quest_pos = await client.quest_position.position()
        for mesh in mesh_list:
            for vertices in mesh:
                if abs(vertices[2] - quest_pos.z) < 700:
                    meshpoints.append(vertices)
                
        #closemeshpoints = [point for point in meshpoints if abs(point[1] - pos.y) < 500]
        mesh2d = []
        for point in meshpoints:
            mesh2d.append([point[0], point[1]]) 
            
        mesh2d = np.array(mesh2d)
        hull = ConvexHull(mesh2d)

        found = False
        radius = 10
        
        capsule_radius = 20
        capsule_length = 10
        #await client.teleport(XYZ(-351.65478515625, 279.5632019042969, 0.0008737124735489488))
        #input()
        while not found:
            for angle in range(360):
                rad = angle * (math.pi / 180)
                direction = (math.cos(rad) * radius, math.sin(rad) * radius)
                position = (quest_pos.x + direction[0], quest_pos.y + direction[1], quest_pos.z)
                if isInHull([[position[0], position[1]]], hull):
                    capsule = (position, capsule_radius, capsule_length) # player capsule
                    if not cube_collision_check(capsule, cube_list):
                        if not cylinder_collision_check(capsule, cylinders_list):
                            if not sphere_collision_check(capsule, sphere_list):
                                print("hi")
                                found = True
                                break
                    
                            else:
                                ic("hit a sphere")
                        else:
                            ic("hit a cylinder")
                    else:
                        ic("hit a box")
            # input()
            radius += 50
            
        await client.teleport(XYZ(*position))

        # import matplotlib.pyplot as plt
        # plt.plot(mesh2d[:,0], mesh2d[:,1], 'o')
        # for simplex in hull.simplices:
        #     plt.plot(mesh2d[simplex, 0], mesh2d[simplex, 1], 'k-')

        # plt.show()
        # from icecream import ic
        # points = []
        # for mesh in mesh_list:
        #     for vertices in mesh:
        #         mesh.append(vertices)

        # for cube in cube_list:
        #     for vertices in cube:
        #         points.append(vertices)
                
        #fig = plt.figure()
        #ax = fig.add_subplot(projection='3d')
        
        #print(pts)
        #hull = ConvexHull(pts)
        #print(hull.simplices)
        
        # ax.plot(pts.T[0], pts.T[1], pts.T[2], "ko")
        # for s in hull.simplices:
        #     s = np.append(s, s[0])  # Here we cycle back to the first coordinate
        #     ax.plot(pts[s, 0], pts[s, 1], pts[s, 2], "r-")

        #edges= zip(*cube_list)
        
        #for simplex in hull.simplices:
        #    print(simplex)
        #await asyncio.sleep(0.3)
        #plt.show()

    finally:
        print("Closing")
        await handler.close()

# if __name__ == "__main__":
#     asyncio.run(testbench())

# # Test the function
# point = (1, 2, 3)
# cylinder = (0, 0, 0, 2, 5)
# #print(point_in_cylinder(*point, *cylinder))  # Output: True