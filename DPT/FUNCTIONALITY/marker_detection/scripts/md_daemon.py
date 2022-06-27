import pathlib
from threading import Thread
import time
import zmq
from src.marker_detection.md_system import MarkerDetectionSystem


def main(args: "dict[str, object]"):
    """Starts the marker detection system without visual output

    Args:
        args (Dict[str, object]): Dictionary of parser arguments
    """

    daemon = MarkerDetectionDaemon(args["ip"], args["port"])
    exit_code = daemon.mds_loop()
    print(f"Marker Detection finished with exit code {exit_code}")


class MarkerDetectionDaemon:
    """A Daemon/Service running the marker_detection system. Uses ZeroMQ to send results.
    
    Each frame it sends the numpy array of detected marker positions and receives an Acknowledgment
    from the server.

    Attributes:
    -----------
    mds : MarkerDetectionSystem
    ip : str
        ip for the zeromq tcp connection
    port : int
        port for the zeromq tcp connection
    """

    def __init__(self, ip, port):
        """Creates marker detection daemon instance

        Args:
            ip (str): ip for the zeromq tcp connection
            port (int): port for the zeromq tcp connection
        """

        settings_file = pathlib.Path(__file__).parent.parent.resolve() \
            / "cli_data" / "md_settings.json"
        calibration_file = pathlib.Path(__file__).parent.parent.resolve() \
            / "cli_data" / "calibration.conf"
        # self.mds = MarkerDetectionSystem(video_ouput=False,
        #    zed2_config_file=calibration_file, settings_file=settings_file)

        self.ip = ip
        self.port = port

    def mds_loop(self) -> int:
        context = zmq.Context()

        socket = context.socket(zmq.REQ)
        socket.setsockopt(zmq.CONFLATE, True)
                        
        with socket.connect("tcp://localhost:3777"):

            incoming_msg = ""
            test_int = 0

            while True:
                #if self.mds.found_charuco == False:
                #    success = self.mds.calibration()
                #    continue

                #video_closed = self.mds.update()

                #if video_closed or self.abort:
                #   break

                #marker_pos = self.mds.get_marker_coordinates()
                time.sleep(0.1)
                
                marker_pos = [123, 23, 23, test_int]
                test_int += 1

                socket.send_pyobj(marker_pos)
                incoming_msg = socket.recv_string(encoding='ascii')
                print(incoming_msg)
                
                if incoming_msg == "STOP":
                    return 1
