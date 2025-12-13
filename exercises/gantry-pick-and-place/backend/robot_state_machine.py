import asyncio
from asyncio import Task
from typing import Any, Coroutine

from state_machine.core import BaseTriggers, StateMachine
from state_machine.decorators import on_enter_state, on_state_change
from state_machine.defs import State, StateGroup, Trigger

from positions import (
    TABLE_A_POLYGON,
    TABLE_B_POLYGON,
    CubeDestinationPosition,
    CubeStartPosition,
)
from robot import Robot

DEFAULT_CUBE_START_POSITION = CubeStartPosition(
    x=TABLE_A_POLYGON.centroid.x,
    y=TABLE_A_POLYGON.centroid.y,
    z=0,
)
DEFAULT_DESTINATION_POSITION = CubeDestinationPosition(
    x=TABLE_B_POLYGON.centroid.x,
    y=TABLE_B_POLYGON.centroid.y,
    z=0,
)
LIFTING_HEIGHT_ABOVE_TABLE: int = 300


class Picking(StateGroup):
    moving = State()
    lowering = State()
    closing = State()


class Transporting(StateGroup):
    lifting = State()
    moving = State()


class Placing(StateGroup):
    lowering = State()
    opening = State()
    lifting = State()


class SequenceFinished(StateGroup):
    finished = State()


class Home(StateGroup):
    home = State()
    moving = State()
    opening = State()


class States:
    home = Home()
    picking = Picking()
    transporting = Transporting()
    placing = Placing()
    sequence_finished = SequenceFinished()


class Triggers:
    start = Trigger("start")
    finished_moving_above_cube: Trigger = Trigger("finished_moving_above_cube")
    finished_lowering_for_pickup: Trigger = Trigger("finished_lowering_for_pickup")
    finished_closing_gripper: Trigger = Trigger("finished_closing_gripper")
    finished_lifting_cube: Trigger = Trigger("finished_lifting_cube")
    finished_moving_above_destination: Trigger = Trigger(
        "finished_moving_above_destination"
    )
    finished_lowering_for_placement: Trigger = Trigger(
        "finished_lowering_for_placement"
    )
    finished_opening_gripper_for_placement: Trigger = Trigger(
        "finished_opening_gripper_for_placement"
    )
    finished_lifting_after_placement: Trigger = Trigger(
        "finished_lifting_after_placement"
    )
    home = Trigger("home")
    finished_moving_to_home: Trigger = Trigger("finished_moving_to_home")
    finished_opening_gripper_at_home: Trigger = Trigger(
        "finished_opening_gripper_at_home"
    )


IDLE_STATES = [
    "ready",
    str(States.home.home),
    str(States.sequence_finished.finished),
]

TRANSITIONS = [
    Triggers.start.transition("ready", States.picking.moving),
    Triggers.start.transition(States.home.home, States.picking.moving),
    Triggers.finished_moving_above_cube.transition(
        States.picking.moving, States.picking.lowering
    ),
    Triggers.finished_lowering_for_pickup.transition(
        States.picking.lowering, States.picking.closing
    ),
    Triggers.finished_closing_gripper.transition(
        States.picking.closing, States.transporting.lifting
    ),
    Triggers.finished_lifting_cube.transition(
        States.transporting.lifting, States.transporting.moving
    ),
    Triggers.finished_moving_above_destination.transition(
        States.transporting.moving, States.placing.lowering
    ),
    Triggers.finished_lowering_for_placement.transition(
        States.placing.lowering, States.placing.opening
    ),
    Triggers.finished_opening_gripper_for_placement.transition(
        States.placing.opening, States.placing.lifting
    ),
    Triggers.finished_lifting_after_placement.transition(
        States.placing.lifting, States.sequence_finished.finished
    ),
    Triggers.home.transition("*", States.home.moving),
    Triggers.finished_moving_to_home.transition(
        States.home.moving, States.home.opening
    ),
    Triggers.finished_opening_gripper_at_home.transition(
        States.home.opening, States.home.home
    ),
]


class RobotStateMachine(StateMachine):
    def __init__(self):
        super().__init__(
            states=States,
            transitions=TRANSITIONS,
            # We want start() to always trigger "start".
            enable_last_state_recovery=False,
        )
        self.robot = Robot()

        # Desired cube positions
        self.next_cube_start_position = DEFAULT_CUBE_START_POSITION
        self.next_cube_end_position = DEFAULT_DESTINATION_POSITION

        # Cube positions used when working above the start or end location
        self._cube_start_position = DEFAULT_CUBE_START_POSITION
        self._cube_end_position = DEFAULT_DESTINATION_POSITION

        self._move_home_requested = False

    def robot_is_idle(self):
        return self.state in IDLE_STATES

    def move_home(self):
        if self.robot_is_idle():
            self.trigger(Triggers.home())
        else:
            print(
                f"Robot is in {self.state}, will move home after the current task completes"
            )
            self._move_home_requested = True

    def spawn(self, coro: Coroutine[Any, Any, Any]) -> Task[Any]:
        """Override spawn() to go to the fault state if an exception is raised by the coroutine"""

        async def _wrapper():
            try:
                await coro
            except Exception as e:
                print(f"ERROR: {e}")
                self.trigger(BaseTriggers.TO_FAULT)

        return super().spawn(_wrapper())

    @on_enter_state(States.picking.moving)
    def _move_above_cube(self, _):
        async def move_above_cube():
            await self.robot.move_to_position(
                [
                    self.next_cube_start_position.x,
                    self.next_cube_start_position.y,
                    LIFTING_HEIGHT_ABOVE_TABLE,
                ]
            )
            self._cube_start_position = self.next_cube_start_position
            self._change_state(Triggers.finished_moving_above_cube)

        self.spawn(move_above_cube())

    @on_enter_state(States.picking.lowering)
    def _lower_for_pickup(self, _):
        async def move_on_cube():
            await self.robot.move_to_position(self._cube_start_position.to_list())
            self._change_state(Triggers.finished_lowering_for_pickup)

        self.spawn(move_on_cube())

    @on_enter_state(States.picking.closing)
    def _close_gripper(self, _):
        async def close_gripper():
            await self.robot.close_gripper()
            self._change_state(Triggers.finished_closing_gripper)

        self.spawn(close_gripper())

    @on_enter_state(States.transporting.lifting)
    def _lift_cube(self, _):
        async def lift_cube():
            await self.robot.move_to_position(
                [
                    self._cube_start_position.x,
                    self._cube_start_position.y,
                    LIFTING_HEIGHT_ABOVE_TABLE,
                ]
            )
            self._change_state(Triggers.finished_lifting_cube)

        self.spawn(lift_cube())

    @on_enter_state(States.transporting.moving)
    def _move_above_destination(self, _):
        async def move_above_destination():
            await self.robot.move_to_position(
                [
                    self.next_cube_end_position.x,
                    self.next_cube_end_position.y,
                    LIFTING_HEIGHT_ABOVE_TABLE,
                ]
            )
            self._cube_end_position = self.next_cube_end_position
            self._change_state(Triggers.finished_moving_above_destination)

        self.spawn(move_above_destination())

    @on_enter_state(States.placing.lowering)
    def _lower_for_placement(self, _):
        async def move_on_destination():
            await self.robot.move_to_position(self._cube_end_position.to_list())
            self._change_state(Triggers.finished_lowering_for_placement)

        self.spawn(move_on_destination())

    @on_enter_state(States.placing.opening)
    def _open_gripper_for_placement(self, _):
        async def open_gripper():
            await self.robot.open_gripper()
            self._change_state(Triggers.finished_opening_gripper_for_placement)

        self.spawn(open_gripper())

    @on_enter_state(States.placing.lifting)
    def _lift_after_placement(self, _):
        async def lift():
            await self.robot.move_to_position(
                [
                    self._cube_end_position.x,
                    self._cube_end_position.y,
                    LIFTING_HEIGHT_ABOVE_TABLE,
                ]
            )
            self._change_state(Triggers.finished_lifting_after_placement)

        self.spawn(lift())

    @on_enter_state(States.home.moving)
    def _move_home(self, _):
        async def move_home():
            self._move_home_requested = False
            await self.robot.move_to_home_position()
            self._change_state(Triggers.finished_moving_to_home)

        self.spawn(move_home())

    @on_enter_state(States.home.opening)
    def _open_gripper_at_home(self, _):
        async def open_gripper():
            await self.robot.open_gripper()
            self._change_state(Triggers.finished_opening_gripper_at_home)

        self.spawn(open_gripper())

    @on_state_change
    def _print_transition(self, old_state: str, new_state: str, trigger: str):
        print(f"{trigger}: {old_state} --> {new_state}")

    def _change_state(self, trigger: Trigger):
        self.trigger((Triggers.home if self._move_home_requested else trigger)())


if __name__ == "__main__":

    async def main():
        machine = RobotStateMachine()
        while True:
            machine.start()
            await asyncio.sleep(60)
            machine.move_home()
            await asyncio.sleep(30)

    asyncio.run(main())
