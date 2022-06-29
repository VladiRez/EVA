"""
author: robert.knobloch@stud.tu-darmstadt.de

Program managing the operational data storage (MongoDB) of the DPT.
PyMongo docs: https://pymongo.readthedocs.io/en/stable/
"""

from pymongo import MongoClient
from pprint import pprint

class OpData:
    """
    Class for interfacing with the Operational Data Storage
    """
    def __init__(self):
        self.client = MongoClient()
        self.db = self.client["dpt_op_data"]

    def add_waypoint(self, key, ):



