"""
Interface to the EVA Robot
See EVA Documentation here:
https://docs.automata.tech/v/4.11.1/
https://eva-python-sdk.readthedocs.io/en/docs-development/

author: robert.knobloch@stud.tu-darmstadt.de
"""
import zmq
from evasdk import Eva
from evasdk.eva_locker import EvaWithLocker
import logging
import signal
from threading import Thread, Lock, Event

from dpt_module import DptModule, Requests, Responses

logging.basicConfig(level=logging.DEBUG)


class EvaInterface(DptModule):

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        signal.signal(signal.SIGINT, self.shutdown)
        signal.signal(signal.SIGTERM, self.shutdown)

        super().__init__("eva_interface")

        host = '192.168.152.106'
        token = '1c097cb9874f6c5e66beb0aba2123eb4038c2a19'

        self.eva = Eva(host, token)
        self.abort = Event()

        self.backdriving_abort = Event()
        self.listening_thread = Thread(target=self.listen_stop_backdriving)

    # Define methods for usage of EvaInterface object with a context manager ("with" statement)
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.shutdown()

    def shutdown(self):
        self.abort.set()
        super().shutdown()
        if self.listening_thread.is_alive():
            self.listening_thread.join()

    def listen(self) -> None:
        """
        Loop for listening to incoming requests.
        Expects a tuple with the first entry being the request type.
        """

        while not self.abort.is_set():
            try:
                (sender, msg) = self.receive()

            # Abort when module is being terminated
            except zmq.ContextTerminated:
                break
            except zmq.error.ZMQError as e:
                if e.errno == zmq.Event.CLOSED.value:
                    break
                else:
                    raise e

            if msg[0] == Requests.SHUTDOWN:
                self.shutdown()
                break

            elif msg[0] == Requests.BACKDRIVING_MODE:
                self.backdriving_mode(sender)


            elif msg[0] == Requests.STOP_BACKDRIVING:
                self.backdriving_abort.set()
                self.backdriving_thread.join()
                self.transmit(sender, Requests.STOP_BACKDRIVING)

    def backdriving_mode(self, sender: str) -> None:
        """
        Listen to EVA waypoint button press, send waypoint to self.set_waypoint method.
        """
        # Clear the backdriving events
        self.backdriving_abort.clear()

        # Thread to listen to the stop command
        self.listening_thread = Thread(target=self.listen_stop_backdriving)
        self.listening_thread.start()

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
                self.transmit(sender, Requests.BACKDRIVING_MODE)
                self.backdriving_abort.wait()
                self.transmit(sender, Requests.STOP_BACKDRIVING)
                self.listening_thread.join()

        if not success:
            self.transmit(sender, Responses.LOCK_FAILED)

    def new_waypoint(self, waypoint: dict[str, object]):
        self.transmit("op_data", (Requests.NEW_WP, waypoint["waypoint"]))
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

    def listen_stop_backdriving(self):
        """
        Loop for listening to incoming requests to stop backdriving.
        """

        while not self.abort.is_set():
            try:
                (sender, msg) = self.receive()

            # Abort when module is being terminated
            except zmq.ContextTerminated:
                break
            except zmq.error.ZMQError as e:
                if e.errno == zmq.Event.CLOSED.value:
                    break
                else:
                    raise e

            if msg == Requests.SHUTDOWN:
                self.shutdown()
                break

            elif msg == Requests.STOP_BACKDRIVING:
                self.backdriving_abort.set()
                break


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


