"""
Interface to the EVA Robot
See EVA Documentation here:
https://docs.automata.tech/v/4.11.1/
https://eva-python-sdk.readthedocs.io/en/docs-development/

author: robert.knobloch@stud.tu-darmstadt.de
"""

from evasdk import Eva
import logging
import signal
from threading import Thread, Lock, Event

from dpt_module import DptModule, Requests, Responses

logging.basicConfig(level=logging.DEBUG)


class EvaInterface(DptModule):

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        signal.signal(signal.SIGINT, self.shutdown)

        host = '172.16.172.1'
        token = '45d1369cacf4eebbd29147839b640862733a7c0a'

        self.eva = Eva(host, token)
        self.abort = False

        self.lock = Lock()
        self.backdriving_abort = Event()
        self.backdriving_success = Event()
        self.backdriving_thread = None

        super().__init__("eva_interface")

    def shutdown(self):
        self.abort = True
        if self.backdriving_thread is not None:
            if self.backdriving_thread.is_alive():
                self.backdriving_abort.set()
                self.backdriving_thread.join()


    def listen(self) -> None:
        """
        Loop for listening to incoming requests.
        Expects a tuple with the first entry being the request type.
        """

        while not self.abort:
            (sender, msg) = self.receive()

            if msg[0] == Requests.SHUTDOWN:
                self.shutdown()
                break

            elif msg[0] == Requests.BACKDRIVING_MODE:
                #self.backdriving_mode()
                # Clear the backdriving events
                self.backdriving_abort.clear()
                self.backdriving_success.clear()

                # Check if there is already a running thread
                if self.backdriving_thread is not None:
                    if self.backdriving_thread.is_alive():
                        self.transmit(sender, Responses.LOCK_FAILED)
                        continue

                self.backdriving_thread = Thread(target=self.backdriving_mode)
                self.backdriving_thread.start()

                success = self.backdriving_success.wait(8)
                if success:
                    self.transmit(sender, Requests.BACKDRIVING_MODE)
                else:
                    self.transmit(sender, Responses.LOCK_FAILED)


            elif msg[0] == Requests.STOP_BACKDRIVING:
                self.backdriving_abort.set()
                self.backdriving_thread.join()


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
            (sender, wp) = self.receive(from_sender="op_data", timeout=1000)
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


    # Threaded methods, these have to be thread-safe
    ###############################################################################################

    def backdriving_mode(self) -> None:
        """
        Listen to EVA waypoint button press, send waypoint to self.set_waypoint method.
        """

        with self.eva.lock(), self.eva.websocket() as ws:
            ws.register("backdriving", self.new_waypoint)
            self.backdriving_success.set()
            self.backdriving_abort.wait()


if __name__ == "__main__":
    eva = EvaInterface()
    eva.backdriving_mode()
    print("finished")