"""
Interface to the EVA Robot
See EVA Documentation here:
https://docs.automata.tech/v/4.11.1/
https://eva-python-sdk.readthedocs.io/en/docs-development/

author: robert.knobloch@stud.tu-darmstadt.de
"""
import requests.exceptions
import zmq
from evasdk import Eva
from evasdk.eva_locker import EvaWithLocker
import logging
import signal
import asyncio
import os
from threading import Thread, Lock, Event

from base_module import BaseModule

logging.basicConfig(level=logging.DEBUG)


class EvaInterface(BaseModule):

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        #signal.signal(signal.SIGINT, self.shutdown)
        #signal.signal(signal.SIGTERM, self.shutdown)

        super().__init__()

        host = '192.168.152.106'
        token = '1c097cb9874f6c5e66beb0aba2123eb4038c2a19'

        self.eva = Eva(host, token)

        self.backdriving_abort = asyncio.Event()

        self.OP_DATA_ADDR = os.environ["OP_DATA_ADDR"]
        self.register_connection(self.OP_DATA_ADDR)
        asyncio.run(self.entrypoint())

    async def entrypoint(self):
        service_loop_task = asyncio.create_task(self.service_loop())
        await service_loop_task

    async def service_loop(self) -> None:
        """
        Loop for listening to incoming requests.
        Expects a tuple with the first entry being the request type.
        """

        while True:
            try:
                (sender, msg) = await self.server_receive()

            # Abort when module is being terminated
            except zmq.ContextTerminated:
                break
            except zmq.error.ZMQError as e:
                if e.errno == zmq.Event.CLOSED.value:
                    break
                else:
                    raise e

            request = msg[0]

            if request == "SHUTDOWN":
                self.shutdown()
                break

            elif request == "BACKDRIVING_MODE":
                self.backdriving_task = create_task(self.backdriving(sender))

            elif request == "STOP_BACKDRIVING":
                self.backdriving_abort.set()
                await self.backdriving_task
                await self.server_transmit(sender, ("STOP_BACKDRIVING",))

            elif request == "GOTO_WP":
                joint_angles = msg[1]
                lock_success = self.goto_wp(joint_angles)
                if lock_success:
                    await self.server_transmit(sender, ("GOTO_WP",))
                else:
                    await self.server_transmit(sender, ("LOCK_FAILED",))

            elif request == "EXECUTE_TP":
                wp_list = msg[1]

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

            else:
                await self.server_transmit(sender, ("UNKNOWN_COMMAND",))

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
            ws.register("backdriving", self.new_waypoint)

            # Uncomment to monitor robot state
            # ws.register("state_change", self.print_state)

            # Context to change the lock renew period
            with EvaWithLocker(eva, fallback_renew_period=2):
                success = True
                await self.server_transmit(sender, ("BACKDRIVING_MODE",))
                await self.backdriving_abort.wait()
                await self.server_transmit(sender, ("STOP_BACKDRIVING",))

        if not success:
            await self.server_transmit(sender, ("LOCK_FAILED",))

    async def new_waypoint(self, waypoint: dict[str, object]):
        await self.server_transmit(self.OP_DATA_ADDR, ("NEW_WP", waypoint["waypoint"]))
        pass

    def goto_zero(self):
        with self.eva.lock():
            self.eva.control_wait_for_ready()
            self.eva.control_go_to([0, 0, 0, 0, 0, 0], mode='teach')

    async def make_toolpath(self, path: tuple[int]):
        """

        Raises:
        -------
        ReceiveTimoutException: If Database could not be reached
        """
        
        return
        """ waypoints = []
        unique_wps = set(path)
        for i in unique_wps:
            await self.server_transmit("op_data", ("Get WP", i))
            # received wp: (wp_id, coordinates)
            (sender, wp) = await self.server_receive(timeout=1000)
            waypoints.append({"label_id": i, "joints": wp[1]})

        toolpath = {
            "metadata": {
                "version": 2,
                "default_max_speed": 0.2,
                "analog_modes": {"i0": "voltage", "i1": "voltage", "o0": "voltage", "o1": "voltage"},
                "next_label_id": 3,
                "payload": 0
            },
            "timeline": [
                {"type": "home", "waypoint_id": 0},
                {"type": "trajectory", "trajectory": "joint_space", "waypoint_id": 1, "time": 2},
                {"type": "trajectory", "trajectory": "joint_space", "waypoint_id": 2}
            ],
            "waypoints": waypoints
        }

        self.logger.debug(toolpath)

        self.eva.toolpaths_save("PyTest", toolpath) """



    # STATIC METHODS
    ###############################################################################################

    @staticmethod
    def print_state(msg):
        # Several state changes should be ignored because they happen so often and
        # clutter the logs
        if "servos.telemetry.position" not in msg["changes"] \
                and "global.inputs" not in msg["changes"] \
                and "servos.telemetry.temperature" not in msg["changes"]:

            print(msg)


if __name__ == "__main__":
    ei = EvaInterface()