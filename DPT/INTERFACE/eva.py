"""
Interface to the EVA Robot
See EVA Documentation here:
https://docs.automata.tech/v/4.11.1/
https://eva-python-sdk.readthedocs.io/en/docs-development/

author: robert.knobloch@stud.tu-darmstadt.de
"""
import time

from evasdk import Eva
import logging
import time

from dpt_module import DptModule

logging.basicConfig(level=logging.DEBUG)

class EvaInterface(DptModule):

    def __init__(self):
        self.logger = logging.getLogger(__name__)

        host = '172.16.172.1'
        token = '45d1369cacf4eebbd29147839b640862733a7c0a'

        self.eva = Eva(host, token)

        super().__init__("eva_interface")
        print(self.socket)

    def backdriving_mode(self):
        """
        Listen to EVA waypoint button press, send waypoint to self.set_waypoint method.
        """
        with self.eva.lock(), self.eva.websocket() as ws:
            ws.register("backdriving", self.new_waypoint)
            time.sleep(5)

    def new_waypoint(self, waypoint: dict[str, object]):
        self.transmit("op_data", ("New WP", waypoint["waypoint"]))
        pass

    def goto_zero(self):
        with self.eva.lock():
            self.eva.control_wait_for_ready()
            self.eva.control_go_to([0, 0, 0, 0, 0, 0], mode='teach')

    def make_toolpath(self, path: tuple[int]):
        """

        Raises:
        -------
        ReceiveTimoutException: If Database could not be reached
        """

        waypoints = []
        unique_wps = set(path)
        for i in unique_wps:
            self.transmit("op_data", ("Get WP", i))
            # received wp: (wp_id, coordinates)
            (sender, wp) = self.receive(timeout=1000)
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

        self.eva.toolpaths_save("PyTest", toolpath)


if __name__ == "__main__":
    eva = EvaInterface()
    eva.backdriving_mode()
    print("finished")