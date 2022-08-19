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

logging.basicConfig(level=logging.DEBUG)

class EvaInterface(BaseModule):
    """ Class for Interfacing with the EVA Automata Robot

    Necessary OS Environment Variables:
    -----------------------------------
    OP_DATA_ADDR: ip or domain dame of the operational data interface
    OP_DATA_NUM_SERVERS: number of op data interface containers/services

    Service requests:
    -----------------
    BACKDRIVING_MODE, STOP_BACKDRIVING, GOTO_WP, EXECUTE_TP
    
    """

    def __init__(self):
        super().__init__("eva-interface", 5557)

        self.OP_DATA_ADDR = "127.0.0.1:5556"
        op_data_server_count = 1
        self.register_connection(self.OP_DATA_ADDR, op_data_server_count)

        # Eva Setup
        host = '192.168.152.106'
        token = '1c097cb9874f6c5e66beb0aba2123eb4038c2a19'
        self.eva = Eva(host, token)

        self.backdriving_task = None

        self.awaitable = self.start(self.service_loop())

    async def service_loop(self) -> None:
        """ Loop for listening to incoming requests.
        Expects a tuple with the first entry being the request type.
        """

        while True:
            (sender, req_id, msg) = await self.server_receive()
            resp_id = req_id

            match msg:
                case ["BACKDRIVING_MODE"]:
                    if self.backdriving_task is not None\
                            and not self.backdriving_task.done() \
                            and not self.backdriving_task.cancelled():
                        await self.server_transmit(sender, resp_id, ("ALREADY_IN_BACKDRIVING_MODE",))
                        continue
                    self.backdriving_task = asyncio.create_task(self.backdriving(sender, resp_id))

                case ["STOP_BACKDRIVING"]:
                    if self.backdriving_task is None \
                            or self.backdriving_task.cancelled() \
                            or self.backdriving_task.done():
                        await self.server_transmit(sender, resp_id, ("NOT_IN_BACKDRIVING_MODE",))
                        continue

                    self.backdriving_task.cancel()
                    try:
                        await self.backdriving_task
                    except asyncio.CancelledError:
                        # Successfully stopped backdriving
                        self.backdriving_task = None
                        await self.server_transmit(sender, resp_id, ("STOP_BACKDRIVING",))

                case ["GOTO_WP", joint_angles]:
                    lock_success = self.goto_wp(joint_angles)
                    if lock_success:
                        await self.server_transmit(sender, resp_id, ("GOTO_WP",))
                    else:
                        await self.server_transmit(sender, resp_id, ("LOCK_FAILED",))

                case ["EXECUTE_TP", unique_wps, timeline]:
                    # See toolpath json notation https://docs.automata.tech/v/4.11.1/api/toolpaths/

                    waypoints_json = []
                    for (wp_number, joint_angles) in enumerate(unique_wps):
                        waypoints_json.append({"label_id": wp_number, "joints": joint_angles})

                    timeline_json = [{
                            "type": "home",
                            "waypoint_id": timeline[0]
                        }]
                    for action in timeline:
                        if action == "GRIP":
                            timeline_json.append({"type": "wait", "condition": {"type": "time",
                                                                                "duration": 0.02}})
                            timeline_json.append(
                                {"type": "output-set", "io": {"location": "base",
                                                              "type": "digital", "index": 0},
                                 "value": False})
                            timeline_json.append({"type": "wait", "condition": {"type": "time",
                                                                                "duration": 0.02}})
                            timeline_json.append(
                                {"type": "output-set", "io": {"location": "base",
                                                              "type": "digital", "index": 1},
                                 "value": True})
                            timeline_json.append({"type": "wait", "condition": {"type": "time",
                                                                                "duration": 0.02}})
                        elif action == "UNGRIP":
                            timeline_json.append({"type": "wait", "condition": {"type": "time",
                                                                                "duration": 0.02}})
                            timeline_json.append(
                                {"type": "output-set", "io": {"location": "base",
                                                              "type": "digital", "index": 1},
                                 "value": False})
                            timeline_json.append({"type": "wait", "condition": {"type": "time",
                                                                                "duration": 0.02}})
                            timeline_json.append(
                                {"type": "output-set", "io": {"location": "base",
                                                              "type": "digital", "index": 0},
                                 "value": True})
                            timeline_json.append({"type": "wait", "condition": {"type": "time",
                                                                                "duration": 0.02}})
                        else:
                            wp_number = action
                            timeline_json.append({"type": "trajectory",
                                    "trajectory": "joint_space", "waypoint_id": wp_number})


                    next_wp_id = len(unique_wps)

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
                        "waypoints": waypoints_json,
                        "timeline": timeline_json
                    }

                    logging.info(f"EVA-INTERFACE: Executing toolpath: {toolpath}")

                    with self.eva.lock():
                        self.eva.control_wait_for_ready()
                        self.eva.toolpaths_use(toolpath)
                        logging.info("done")
                        self.eva.control_home()
                        self.eva.control_run(loop=1, mode='teach')


                case _:
                    await self.server_transmit(sender, resp_id, ("UNKNOWN_REQUEST",))

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

    async def backdriving(self, sender: str, resp_id: bytes) -> None:
        """
        Listen to EVA waypoint button press, send waypoint to self.set_waypoint method.

        :param sender: the string of the address to return a response to.
        """

        success = False
        with self.eva.lock() as eva, self.eva.websocket() as ws:

            # Execute method new_waypoint and pass the waypoint when the waypoint button is pressed
            # (see eva websocket docs)
            ws.register("backdriving", self.new_waypoint)

            # Context to change the lock renew period
            with EvaWithLocker(eva, fallback_renew_period=2):
                success = True
                # Confirm successful backdriving
                await self.server_transmit(sender, resp_id, ("BACKDRIVING_MODE",))

                # Keep in loop until task is cancelled
                while True:
                    await asyncio.sleep(1)


        if not success:
            await self.server_transmit(sender, resp_id, ("LOCK_FAILED",))

    def new_waypoint(self, waypoint: dict[str, object]):
        # TODO Not working because of address
        asyncio.run(self.client_transmit(self.OP_DATA_ADDR, ("NEW_WP", waypoint["waypoint"])))

    def goto_zero(self):
        with self.eva.lock():
            self.eva.control_wait_for_ready()
            self.eva.control_go_to([0, 0, 0, 0, 0, 0], mode='teach')


if __name__ == "__main__":
    ei = EvaInterface()