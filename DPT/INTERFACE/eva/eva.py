"""
Interface to the EVA Robot
See EVA Documentation here:
https://docs.automata.tech/v/4.11.1/
https://eva-python-sdk.readthedocs.io/en/docs-development/

author: robert.knobloch@stud.tu-darmstadt.de
"""

import os
import logging
import asyncio

from evasdk import Eva
from evasdk.eva_locker import EvaWithLocker

from base_module import BaseModule


class EvaInterface(BaseModule):
    """ Class for Interfacing with the EVA Automata Robot

    Service requests:
    -----------------
    BACKDRIVING_MODE, STOP_BACKDRIVING, GOTO_WP, EXECUTE_TP
    
    """

    def __init__(self):
        super().__init__()

        self.OP_DATA_ADDR = os.environ["OP_DATA_ADDR"]
        self.register_connection(self.OP_DATA_ADDR) 

        # Eva Setup
        host = '192.168.152.106'
        token = '1c097cb9874f6c5e66beb0aba2123eb4038c2a19'
        self.eva = Eva(host, token)

        self.backdriving_task = None

        self.start(self.service_loop())

    async def service_loop(self) -> None:
        """ Loop for listening to incoming requests.
        Expects a tuple with the first entry being the request type.
        """

        while True:
            (sender, msg) = await self.server_receive()

            match msg:
                case ["BACKDRIVING_MODE"]:
                    if self.backdriving_task is not None:
                        await self.server_transmit(sender, ("ALREADY_IN_BACKDRIVING_MODE",))
                        continue
                    self.backdriving_task = asyncio.create_task(self.backdriving(sender))

                case ["STOP_BACKDRIVING"]:
                    if self.backdriving_task is None:
                        await self.server_transmit(sender, ("NOT_IN_BACKDRIVING_MODE",))
                        continue
                    self.backdriving_task.cancel()
                    try:
                        await self.backdriving_task
                    except asyncio.CancelledError:
                        # Successfully stopped backdriving
                        self.backdriving_task = None
                        await self.server_transmit(sender, ("STOP_BACKDRIVING",))

                case ["GOTO_WP", joint_angles]:
                    lock_success = self.goto_wp(joint_angles)
                    if lock_success:
                        await self.server_transmit(sender, ("GOTO_WP",))
                    else:
                        await self.server_transmit(sender, ("LOCK_FAILED",))

                case ["EXECUTE_TP", wp_list]:
                    timeline = [{
                            "type": "home",
                            "waypoint_id": wp_list[0]["label_id"]
                        }]
                    timeline_residuum = [{"type": "trajectory", "trajectory": "joint_space", "waypoint_id": wp["label_id"]} for wp in wp_list]
                    timeline = timeline + timeline_residuum

                    next_wp_id = wp_list[-1]["label_id"] + 1

                    toolpath = {
                        "metadata": {
                            "version": 2,
                            "default_max_speed": 0.25,
                            "payload": 0,
                            "analog_modes": {
                                "i0": "voltage",
                                "i1": "voltage",
                                "o0": "voltage",
                                "o1": "voltage"
                            },
                            "next_label_id": next_wp_id
                        },
                        "waypoints": wp_list,
                        "timeline": timeline
                    }

                    with self.eva.lock():
                        self.eva.control_wait_for_ready()
                        self.eva.toolpaths_use(toolpath)
                        self.eva.control_home()
                        self.eva.control_run(loop=1, mode='teach')

                case _:
                    await self.server_transmit(sender, ("UNKNOWN_REQUEST",))

    def goto_wp(self, joint_angles: list[float]) -> bool:
        """

        :param joint_angles: list of six floats representing the joint angles
        :return: True if lock was successful
        """

        lock_success = False
        with self.eva.lock():
            lock_success = True
            self.eva.control_go_to(joints=joint_angles)

        return lock_success

    async def backdriving(self, sender: str) -> None:
        """
        Listen to EVA waypoint button press, send waypoint to self.set_waypoint method.

        :param sender: the string of the address to return a response to.
        """
        # Clear the backdriving events
        self.backdriving_abort.clear()

        success = False
        with self.eva.lock() as eva, self.eva.websocket() as ws:

            # Execute method new_waypoint and pass the waypoint when the waypoint button is pressed
            # (see eva websocket docs)
            ws.register("backdriving", await self.new_waypoint)

            # Context to change the lock renew period
            with EvaWithLocker(eva, fallback_renew_period=2):
                success = True
                # Confirm successful backdriving
                await self.server_transmit(sender, ("BACKDRIVING_MODE",))

                # Keep in loop until task is cancelled
                try:
                    while True:
                        await asyncio.sleep(1)
                except asyncio.CancelledError:
                    # Confirm abort backdriving
                    await self.server_transmit(sender, ("STOP_BACKDRIVING",))
                    raise

        if not success:
            await self.server_transmit(sender, ("LOCK_FAILED",))

    async def new_waypoint(self, waypoint: dict[str, object]):
        await self.server_transmit(self.OP_DATA_ADDR, ("NEW_WP", waypoint["waypoint"]))
        pass

    def goto_zero(self):
        with self.eva.lock():
            self.eva.control_wait_for_ready()
            self.eva.control_go_to([0, 0, 0, 0, 0, 0], mode='teach')


if __name__ == "__main__":
    ei = EvaInterface()