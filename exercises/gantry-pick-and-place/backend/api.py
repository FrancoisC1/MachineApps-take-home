import asyncio
from contextlib import asynccontextmanager
from typing import Optional

import uvicorn
from communication.app import VentionApp
from communication.decorators import action, stream
from fastapi import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from starlette.status import HTTP_409_CONFLICT
from transitions import MachineError

from positions import (
    CubeDestinationPosition,
    CubeStartPosition,
    Position,
    RobotHomePosition,
)
from robot_state_machine import RobotStateMachine

STREAM_PUBLISH_INTERVAL_SEC = 0.1


class RobotStatus(BaseModel):
    state_machine_state: str
    idle: bool
    gripper_open: bool


class ErrorInfo(BaseModel):
    """Error structure returned by vention-communication upon error"""

    code: str
    message: str


class EmptyOrErrorResponse(BaseModel):
    error: Optional[ErrorInfo] = None


state_machine = RobotStateMachine()


@asynccontextmanager
async def _lifespan(_):
    """Continually publish the streams during the lifespan of the app"""

    async def _publish_streams():
        while True:
            await stream_robot_position()
            await stream_robot_status()
            await asyncio.sleep(STREAM_PUBLISH_INTERVAL_SEC)

    asyncio.create_task(_publish_streams())
    yield


app = VentionApp(
    name="RobotControl",
    title="Robot State Machine API",
    description="API for controlling and monitoring a pick-and-place gantry robot",
    version="1.0.0",
    emit_proto=True,
    proto_path="proto/robot_control.proto",
    lifespan=_lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)


@action()
async def get_robot_position() -> Position:
    return Position.from_list(state_machine.robot.get_current_position())


@action()
async def get_robot_home_position() -> RobotHomePosition:
    return RobotHomePosition.from_list(state_machine.robot.get_home_position())


@action()
async def set_robot_home_position(request: RobotHomePosition) -> EmptyOrErrorResponse:
    state_machine.robot.set_home_position(request.to_list())
    return EmptyOrErrorResponse()


@action()
async def get_robot_status() -> RobotStatus:
    return RobotStatus(
        state_machine_state=state_machine.state,
        idle=state_machine.robot_is_idle(),
        gripper_open=state_machine.robot.gripper_is_open(),
    )


@action()
async def start_sequence() -> EmptyOrErrorResponse:
    try:
        state_machine.start()
    except MachineError:
        raise HTTPException(
            HTTP_409_CONFLICT,
            f"Cannot start the sequence while the robot is in state {state_machine.state}",
        )
    return EmptyOrErrorResponse()


@action()
async def move_home() -> EmptyOrErrorResponse:
    state_machine.move_home()
    return EmptyOrErrorResponse()


@action()
async def get_cube_start_position() -> CubeStartPosition:
    return state_machine.next_cube_start_position


@action()
async def set_cube_start_position(position: CubeStartPosition) -> EmptyOrErrorResponse:
    state_machine.next_cube_start_position = position
    return EmptyOrErrorResponse()


@action()
async def get_cube_destination_position() -> CubeDestinationPosition:
    return state_machine.next_cube_end_position


@action()
async def set_cube_destination_position(
    position: CubeDestinationPosition,
) -> EmptyOrErrorResponse:
    state_machine.next_cube_end_position = position
    return EmptyOrErrorResponse()


@stream(name="robot_position_stream", payload=Position)
async def stream_robot_position() -> Position:
    return Position.from_list(state_machine.robot.get_current_position())


@stream(name="robot_status_stream", payload=RobotStatus)
async def stream_robot_status() -> RobotStatus:
    return RobotStatus(
        state_machine_state=state_machine.state,
        idle=state_machine.robot_is_idle(),
        gripper_open=state_machine.robot.gripper_is_open(),
    )


app.finalize()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
