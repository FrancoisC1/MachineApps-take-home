import asyncio

from robot_sim import GripperState
from robot_sim import Robot as RobotSim

REGULAR_MOVEMENT_SPEED = 95
HOME_MOVEMENT_SPEED = 50
MOVEMENT_PERIOD_SEC = 0.1
GRIPPER_ACTION_DELAY_SEC = 2.0


class Robot:
    def __init__(self):
        self._robot_sim = RobotSim()

    def set_home_position(self, position: list[float]):
        self._robot_sim.home_position = position
        # Force a motion replan
        self._robot_sim.axis_speed = [0, 0, 0]

    def get_home_position(self) -> list[float]:
        return self._robot_sim.home_position

    def get_current_position(self) -> list[float]:
        return self._robot_sim.current_position

    def gripper_is_open(self) -> bool:
        return self._robot_sim.gripper_state is GripperState.OPEN

    async def move_to_home_position(self):
        while self._robot_sim.current_position != self._robot_sim.home_position:
            move_result = self._robot_sim.move_home(speed=HOME_MOVEMENT_SPEED)
            if move_result.error:
                raise RuntimeError(move_result.error)
            await asyncio.sleep(MOVEMENT_PERIOD_SEC)

    async def move_to_position(self, position: list[float]):
        while self._robot_sim.current_position != position:
            move_result = self._robot_sim.move_to(
                target_position=position,
                speed=REGULAR_MOVEMENT_SPEED,
            )
            if move_result.error:
                raise RuntimeError(move_result.error)
            await asyncio.sleep(MOVEMENT_PERIOD_SEC)

    async def open_gripper(self):
        await asyncio.sleep(GRIPPER_ACTION_DELAY_SEC)
        self._robot_sim.open_gripper()

    async def close_gripper(self):
        await asyncio.sleep(GRIPPER_ACTION_DELAY_SEC)
        self._robot_sim.closed_gripper()
