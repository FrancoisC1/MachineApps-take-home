import math
from typing import Annotated, List

from pydantic import BaseModel, Field
from shapely import affinity
from shapely.geometry import Point, box

WORK_AREA_SIZE = 2000
TABLE_DISTANCE_FROM_EDGE = 100
TABLE_SIZE = 500
TABLE_SQUARE = box(-TABLE_SIZE / 2, -TABLE_SIZE / 2, TABLE_SIZE / 2, TABLE_SIZE / 2)

TABLE_A_CORNER_X = -(WORK_AREA_SIZE / 2 - TABLE_DISTANCE_FROM_EDGE)
TABLE_A_CORNER_Y = -TABLE_A_CORNER_X
TABLE_A_CENTER_X = TABLE_A_CORNER_X + TABLE_SIZE / 2
TABLE_A_CENTER_Y = TABLE_A_CORNER_Y - TABLE_SIZE / 2
TABLE_A_POLYGON = affinity.translate(TABLE_SQUARE, TABLE_A_CENTER_X, TABLE_A_CENTER_Y)

TABLE_B_RIGHT_CORNER_X = WORK_AREA_SIZE / 2 - TABLE_DISTANCE_FROM_EDGE
TABLE_B_BOTTOM_CORNER_Y = -TABLE_B_RIGHT_CORNER_X
TABLE_B_CORNER_TO_CENTER = TABLE_SIZE / math.sqrt(2)
TABLE_B_CENTER_X = TABLE_B_RIGHT_CORNER_X - TABLE_B_CORNER_TO_CENTER
TABLE_B_CENTER_Y = TABLE_B_BOTTOM_CORNER_Y + TABLE_B_CORNER_TO_CENTER
rotated_table_b_polygon = affinity.rotate(TABLE_SQUARE, 45, origin="center")
TABLE_B_POLYGON = affinity.translate(
    rotated_table_b_polygon, TABLE_B_CENTER_X, TABLE_B_CENTER_Y
)


class Position(BaseModel):
    x: float
    y: float
    z: float

    @classmethod
    def from_list(cls, pos: List[float]):
        return cls(x=pos[0], y=pos[1], z=pos[2])

    def to_list(self) -> List[float]:
        return [self.x, self.y, self.z]


class CubePosition(Position):
    z: Annotated[float, Field(default=0, ge=0, le=0)]


class CubeStartPosition(CubePosition):
    def model_post_init(self, _):
        if not TABLE_A_POLYGON.contains(Point(self.x, self.y)):
            raise ValueError(
                f"Cube start position (x={self.x}, y={self.y}, z={self.z}) is outside Table A bounds"
            )


class CubeDestinationPosition(CubePosition):
    def model_post_init(self, _):
        if not TABLE_B_POLYGON.contains(Point(self.x, self.y)):
            raise ValueError(
                f"Destination position (x={self.x}, y={self.y}, z={self.z}) is outside Table B bounds"
            )


class RobotHomePosition(Position):
    x: Annotated[float, Field(default=0, ge=-WORK_AREA_SIZE / 2, le=WORK_AREA_SIZE / 2)]
    y: Annotated[float, Field(default=0, ge=-WORK_AREA_SIZE / 2, le=WORK_AREA_SIZE / 2)]
    z: Annotated[float, Field(default=0, ge=0, le=WORK_AREA_SIZE / 2)]
