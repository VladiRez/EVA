"""
author: robert.knobloch@stud.tu-darmstadt.de

Program managing the operational data storage (MongoDB) of the DPT.
PyMongo docs: https://pymongo.readthedocs.io/en/stable/
"""

from pymongo import MongoClient
from pprint import pprint

from dpt_module import DptModule, Requests

class OpData(DptModule):
    """
    Class for interfacing with the Operational Data Storage
    """
    def __init__(self):
        self.client = MongoClient()
        self.db = self.client["dpt_op_data"]

        super().__init__("op_data")

    def listen(self):
        """
        Receivable messages:
        from EvaInterface:
            ("New WP", waypoint : tuple[float * 6])
            ("Get WP", waypoint_id : int)

        :raises
        NonexistentWaypointException: If no Waypoint with given ID could be found ("Get ID")
        """

        while True:

            col_waypoints = self.db["waypoints"]
            (sender, msg) = self.receive()

            if msg[0] == Requests.NEW_WP:
                post = {"wp_id": 3,
                        "coordinates": msg[1]}
                wp_id = col_waypoints.insert_one(post).inserted_id
                print(f"\n New WP with ID {wp_id}")

            elif msg[0] == Requests.GET_WP:
                wp_id = msg[1]
                if not isinstance(wp_id, int):
                    raise ValueError
                wp_doc = col_waypoints.find_one({"wp_id": wp_id})
                if wp_doc is None:
                    raise NonexistentWaypointException
                wp = wp_doc["coordinates"]
                self.transmit(sender, (wp_id, wp))

            elif msg[0] == Requests.GET_ALL_WP_IDS:

                wp_all_ids_cursor = col_waypoints.find({}, {"wp_id": True})
                wp_all_ids = [wp["wp_id"] for wp in wp_all_ids_cursor]
                print(wp_all_ids)
                self.transmit(sender, wp_all_ids)


class NonexistentWaypointException(Exception):
    def __init__(self,*args,**kwargs):
        Exception.__init__(self,*args,**kwargs)




