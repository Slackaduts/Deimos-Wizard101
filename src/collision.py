# Copyright 2022 PeechezNCreem
#
# Licensed under the ISC license:
#
# Permission to use, copy, modify, and/or distribute this software for any purpose with
# or without fee is hereby granted, provided that the above copyright notice and this
# permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES WITH REGARD
# TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS. IN
# NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY SPECIAL, DIRECT, INDIRECT, OR
# CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR
# PROFITS, WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION,
# ARISING OUT OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

from __future__ import annotations

import struct
from dataclasses import dataclass, field
from enum import Enum, Flag
from io import BytesIO
from pathlib import Path
from typing import TypeAlias
from xml.etree import ElementTree as etree
from wizwalker import Wad, Client, XYZ

Matrix3x3: TypeAlias = tuple[
    float, float, float,
    float, float, float,
    float, float, float,
]
SimpleFace: TypeAlias = tuple[int, int, int]
SimpleVert: TypeAlias = tuple[float, float, float]
Vector3D: TypeAlias = tuple[float, float, float]


class StructIO(BytesIO):
    def read_string(self) -> str:
        length, = self.unpack("<i")
        return self.read(length).decode()

    def unpack(self, fmt: str) -> tuple:
        return struct.unpack(fmt, self.read(struct.calcsize(fmt)))


def flt(x: str) -> str:
    x, y = str(round(x, 4)).split(".")

    y = y.ljust(4, "0")

    return f"{x}.{y}"


class ProxyType(Enum):
    BOX = 0
    RAY = 1
    SPHERE = 2
    CYLINDER = 3
    TUBE = 4
    PLANE = 5
    MESH = 6
    INVALID = 7

    @property
    def xml_value(self) -> str:
        return str(self).split(".")[1].lower()


class CollisionFlag(Flag):
    OBJECT = 1 << 0
    WALKABLE = 1 << 1
    HITSCAN = 1 << 3
    LOCAL_PLAYER = 1 << 4
    WATER = 1 << 6
    CLIENT_OBJECT = 1 << 7
    TRIGGER = 1 << 8
    FOG = 1 << 9
    GOO = 1 << 10
    FISH = 1 << 11

    @property
    def xml_value(self) -> str:
        if CollisionFlag.WALKABLE in self:
            return "CT_Walkable"
        elif CollisionFlag.WATER in self:
            return "CT_Water"
        elif CollisionFlag.TRIGGER in self:
            return "CT_Trigger"
        elif CollisionFlag.OBJECT in self:
            return "CT_Object"
        elif CollisionFlag.LOCAL_PLAYER in self:
            return "CT_LocalPlayer"
        elif CollisionFlag.HITSCAN in self:
            return "CT_Hitscan"
        elif CollisionFlag.FOG in self:
            return "CT_Fog"
        elif CollisionFlag.CLIENT_OBJECT in self:
            return "CT_ClientObject"
        elif CollisionFlag.GOO in self:
            return "CT_Goo"
        elif CollisionFlag.FISH in self:
            return "CT_Fish"
        else:
            return "CT_None"


@dataclass
class GeomParams:
    proxy: ProxyType

    @classmethod
    def from_stream(self, stream: StructIO) -> "GeomParams":
        pass

    def save_xml(self, parent: etree.Element) -> None:
        pass


@dataclass
class BoxGeomParams(GeomParams):
    length: float
    width: float
    depth: float

    @classmethod
    def from_stream(cls, stream: StructIO) -> "BoxGeomParams":
        return cls(ProxyType.BOX, *stream.unpack("<fff"))

    def save_xml(self, parent: etree.Element) -> None:
        etree.SubElement(
            parent,
            "dimensions",
            {
                "l": flt(self.length),
                "w": flt(self.width),
                "d": flt(self.depth),
            },
        )


@dataclass
class RayGeomParams(GeomParams):
    position: float
    direction: float
    length: float

    @classmethod
    def from_stream(cls, stream: StructIO) -> "RayGeomParams":
        return cls(ProxyType.RAY, *stream.unpack("<fff"))

    def save_xml(self, parent: etree.Element) -> None:
        pass  # WARNING: KI doesn't load these from xml!!!!


@dataclass
class SphereGeomParams(GeomParams):
    radius: float

    @classmethod
    def from_stream(cls, stream: StructIO) -> "SphereGeomParams":
        return cls(ProxyType.SPHERE, *stream.unpack("<f"))

    def save_xml(self, parent: etree.Element) -> None:
        etree.SubElement(
            parent,
            "radius",
            {"value": flt(self.radius)},
        )


@dataclass
class CylinderGeomParams(GeomParams):
    radius: float
    length: float

    @classmethod
    def from_stream(cls, stream: StructIO) -> "CylinderGeomParams":
        return cls(ProxyType.CYLINDER, *stream.unpack("<ff"))

    def save_xml(self, parent: etree.Element) -> None:
        etree.SubElement(
            parent,
            "cylinder",
            {
                "radius": flt(self.radius),
                "length": flt(self.length),
            },
        )


@dataclass
class TubeGeomParams(GeomParams):
    radius: float
    length: float

    @classmethod
    def from_stream(cls, stream: StructIO) -> "TubeGeomParams":
        return cls(ProxyType.TUBE, *stream.unpack("<ff"))

    def save_xml(self, parent: etree.Element) -> None:
        etree.SubElement(
            parent,
            "tube",
            {
                "radius": flt(self.radius),
                "length": flt(self.length),
            },
        )


@dataclass
class PlaneGeomParams(GeomParams):
    normal: Vector3D
    distance: float

    @classmethod
    def from_stream(cls, stream: StructIO) -> "PlaneGeomParams":
        *normal, distance = stream.unpack("<ffff")
        return cls(ProxyType.PLANE, normal, distance)

    def save_xml(self, parent: etree.Element) -> None:
        etree.SubElement(
            parent,
            "plane",
            {
                "a": flt(self.normal[0]),
                "b": flt(self.normal[1]),
                "c": flt(self.normal[2]),
                "d": flt(self.distance),
            },
        )


@dataclass
class MeshGeomParams(GeomParams):
    @classmethod
    def from_stream(cls, stream: StructIO) -> "MeshGeomParams":
        return cls(ProxyType.MESH)

    def save_xml(self, parent: etree.Element) -> None:
        pass


@dataclass
class ProxyGeometry:
    category_flags: CollisionFlag
    collide_flag: CollisionFlag
    name: str = ""
    rotation: Matrix3x3 = (0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
    location: XYZ = XYZ(0.0, 0.0, 0.0)
    scale: float = 0.0
    material: str = ""
    proxy: ProxyType = ProxyType.INVALID
    params: GeomParams = None

    def load(self, stream: StructIO) -> ProxyGeometry:
        self.name = stream.read_string()
        self.rotation = stream.unpack("<fffffffff")
        self.location = stream.unpack("<fff")
        self.scale, = stream.unpack("<f")
        self.material = stream.read_string()
        self.proxy = ProxyType(*stream.unpack("<i"))

        match ProxyType(self.proxy):
            case ProxyType.BOX:
                self.params = BoxGeomParams.from_stream(stream)
            case ProxyType.RAY:
                self.params = RayGeomParams.from_stream(stream)
            case ProxyType.SPHERE:
                self.params = SphereGeomParams.from_stream(stream)
            case ProxyType.CYLINDER:
                self.params = CylinderGeomParams.from_stream(stream)
            case ProxyType.TUBE:
                self.params = TubeGeomParams.from_stream(stream)
            case ProxyType.PLANE:
                self.params = PlaneGeomParams.from_stream(stream)
            case ProxyType.MESH:
                self.params = MeshGeomParams.from_stream(stream)
            case _:
                raise ValueError(f"Invalid proxy type: {self.proxy}")

    def save_xml(self, parent: etree.Element) -> etree.Element:
        element = etree.SubElement(
            parent,
            "primitive",
            {
                "type": self.proxy.xml_value,
                "name": self.name,
                "category": self.category_flags.xml_value,
                "material": self.material,
            },
        )

        if self.proxy == ProxyType.MESH:
            pass
        else:
            self.params.save_xml(element)

        x, y, z = self.location
        etree.SubElement(
            element,
            "location",
            {"x": flt(x), "y": flt(y), "z": flt(z)},
        )

        etree.SubElement(
            element,
            "rotation",
            {"matrix": " ".join(flt(x) for x in self.rotation)},
        )

        return element


@dataclass
class ProxyMesh(ProxyGeometry):
    vertices: list[SimpleVert] = field(default_factory=list)
    faces: list[SimpleFace] = field(default_factory=list)
    normals: list[SimpleVert] = field(default_factory=list)

    def load(self, stream: StructIO) -> None:
        vertex_count, face_count = stream.unpack("<ii")
        for _ in range(vertex_count):
            self.vertices.append(stream.unpack("<fff"))

        for _ in range(face_count):
            self.faces.append(stream.unpack("<iii"))
            self.normals.append(stream.unpack("<fff"))

        super().load(stream)

    def save_xml(self, parent: etree.Element) -> etree.Element:
        element = super().save_xml(parent)

        mesh = etree.SubElement(element, "mesh")

        vertexlist = etree.SubElement(
            mesh,
            "vertexlist",
            {"size": str(len(self.vertices))},
        )
        for x, y, z in self.vertices:
            etree.SubElement(
                vertexlist,
                "vert",
                {"x": flt(x), "y": flt(y), "z": flt(z)},
            )

        facelist = etree.SubElement(
            mesh,
            "facelist",
            {"size": str(len(self.faces))},
        )
        for a, b, c in self.faces:
            etree.SubElement(facelist, "face", {"a": str(a), "b": str(b), "c": str(c)})

        return element


@dataclass
class CollisionWorld:
    objects: list[ProxyGeometry] = field(default_factory=list)

    def load(self, raw_data: bytes) -> None:
        stream = StructIO(raw_data)

        geometry_count, = stream.unpack("<i")
        for _ in range(geometry_count):
            # category_bits and collide_bits are for Open Dynamics Engine
            geometry_type, category_bits, collide_bits = stream.unpack("<iII")

            proxy = ProxyType(geometry_type)
            category = CollisionFlag(category_bits)
            collide = CollisionFlag(collide_bits)

            if proxy == ProxyType.MESH:
                geometry = ProxyMesh(category, collide)
            else:
                geometry = ProxyGeometry(category, collide)

            geometry.load(stream)
            self.objects.append(geometry)

    def save_xml(self, path: str | Path) -> etree.Element:
        world = etree.Element("world")
        for obj in self.objects:
            obj.save_xml(world)

        etree.indent(world)
        path.parent.mkdir(exist_ok=True, parents=True)
        with path.open("w") as file:
            file.write('<?xml version="1.0" encoding="utf-8" ?>\n')
            file.write(etree.tostring(world, encoding="unicode", xml_declaration=False))


async def load_wad(path: str):
    if path is not None:
        return Wad.from_game_data(path.replace("/", "-"))


async def get_collision_data(client: Client = None, zone_name: str = None) -> bytes:
    if not zone_name and client:
        zone_name = await client.zone_name()

    elif not zone_name and not client:
        raise Exception('Client and/or zone name not provided, cannot read collision.bcd.')

    wad = await load_wad(zone_name)
    collision_data = await wad.get_file("collision.bcd")

    return collision_data