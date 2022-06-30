"""
Interface to the EVA Robot
See EVA Documentation here:
https://docs.automata.tech/v/4.11.1/
https://eva-python-sdk.readthedocs.io/en/docs-development/

author: robert.knobloch@stud.tu-darmstadt.de
"""

import evasdk
import logging

from dpt_module import DptModule

logging.basicConfig(level=logging.DEBUG)

class EvaInterface(DptModule):

    def __init__(self):
        host = '172.16.172.1'
        token = '45d1369cacf4eebbd29147839b640862733a7c0a'

        self.eva = evasdk.Eva(host, token)

        super().__init__("eva_interface")
        print(self.socket)

    def backdriving_mode(self):
        """
        Listen to EVA waypoint button press, send waypoint to self.set_waypoint method.
        """
        with self.eva.websocket() as ws:
            ws.register("backdriving", self.new_waypoint)

    def new_waypoint(self, waypoint):
        self.transmit("op_data", ("New WP", waypoint))
        pass

    def goto_zero(self):
        with self.eva.lock():
            self.eva.control_wait_for_ready()
            self.eva.control_go_to([0, 0, 0, 0, 0, 0], mode='teach')

if __name__ == "__main__":
    eva = EvaInterface()
    eva.goto_zero()