"""
author: robert.knobloch@stud.tu-darmstadt.de

Program managing the operational data storage (MongoDB) of the DPT.
PyMongo docs: https://pymongo.readthedocs.io/en/stable/
"""

from pymongo import MongoClient
from pprint import pprint

from dpt_module import DptModule

class OpData(DptModule):
    """
    Class for interfacing with the Operational Data Storage
    """
    def __init__(self):
        self.client = MongoClient()
        self.db = self.client["dpt_op_data"]

        super().__init__()

    def listen(self):
        """
        Receivable messages:
        from EvaInterface:
            ("New WP", waypoint : set[float * 6])
        """
        (sender, msg) = self.receive()

        if msg[0] == "New WP":
            pass





