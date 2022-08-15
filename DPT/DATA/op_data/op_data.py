"""
author: robert.knobloch@stud.tu-darmstadt.de

Program managing the operational data storage (MongoDB) of the DPT.
PyMongo docs: https://pymongo.readthedocs.io/en/stable/
"""

from pymongo import MongoClient
from bson.objectid import ObjectId
import time
import logging
import signal
import asyncio
import os


from base_module import BaseModule

class OpData(BaseModule):
    """
    Class for interfacing with the Operational Data Storage

    Necessary OS Environment Variables:
    -----------------------------------
    DB_ADDRESS: ip or domain dame of the mongodb database

    Service requests:
    -----------------
    SHUTDOWN, NEW_WP, GET_WP, GET_ALL_WP_IDS, CHANGE_WP_NAME, NEW_TP, GET_TP, ADD_TO_TP,
    RM_FROM_TP 
    """

    def __init__(self):
        super().__init__()

        # MongoDB Setup
        db_address = os.environ["DB_ADDRESS"]
        self.client = MongoClient(db_address)
        self.db = self.client["dpt_op_data"]

        self.start(self.service_loop())

    async def service_loop(self) -> None:
        """
        Loop for listening to incoming requests.
        Expects a tuple with the first entry being the request type.
        """

        while True:

            col_waypoints = self.db["waypoints"]
            toolpaths = self.db["toolpaths"]
            (sender, msg) = await self.server_receive()

            match msg:
                case ["SHUTDOWN"]:
                    break
                case ["NEW_WP", joint_angles]:
                    post = {"coordinates": joint_angles,
                        "wp_name": "New WP",
                        "creation_time": time.time()}
                    wp_id = col_waypoints.insert_one(post).inserted_id

                case ["GET_WP", wp_id]:
                    wp_id = ObjectId(wp_id) # Convert to mongodb id object
                    wp_doc = col_waypoints.find_one(wp_id)
                    if wp_doc is None:
                        await self.server_transmit(sender, ("NONEXISTENT_OBJECT", str(wp_id)))
                        continue

                    wp_coor = wp_doc["coordinates"]
                    wp_name = wp_doc["wp_name"]
                    wp_time = wp_doc["creation_time"]
                    await self.server_transmit(sender, 
                        ("GET_WP", str(wp_id), wp_name, wp_coor, wp_time))
                
                case ["GET_ALL_WP_IDS"]:
                    all_wps_cursor = col_waypoints.find({})
                    wp_all_ids = [str(wp["_id"]) for wp in all_wps_cursor]
                    all_wps_cursor = col_waypoints.find({})
                    wp_all_names = [wp["wp_name"] for wp in all_wps_cursor]
                    await self.server_transmit(sender, ("GET_ALL_WP_IDS", wp_all_ids, wp_all_names))

                case ["DEL_WP", wp_id]:
                    wp_id = ObjectId(wp_id)
                    result = col_waypoints.delete_one({"_id": wp_id})
                    if result.acknowledged and result.deleted_count == 1:
                        await self.server_transmit(sender, ("DEL_WP",))
                    else:
                        await self.server_transmit(sender, ("UNEXPECTED_FAILURE",))

                case ["CHANGE_WP_NAME", wp_id, wp_name]:
                    wp_id = ObjectId(wp_id)
                    new_value = {"$set": {"wp_name": wp_name}}
                    result = col_waypoints.update_one({"_id": wp_id}, new_value)
                    if result.acknowledged and result.modified_count == 1:
                        await self.server_transmit(sender, ("CHANGE_WP_NAME",))
                    else:
                        await self.server_transmit(sender, ("UNEXPECTED_FAILURE",))
                
                case ["NEW_TP"]:
                    pass

                case ["GET_TP", tp_id]:
                    tp_id = ObjectId(tp_id)
                    tp_doc = toolpaths.find_one(tp_id)
                    if tp_doc is None:
                        await self.server_transmit(sender, ("NONEXISTENT_OBJECT", str(tp_id)))
                        continue

                    wp_list = tp_doc["wps"]
                    await self.server_transmit(sender, ("GET_TP", str(tp_id), wp_list))

                case ["ADD_TO_TP", tp_id, wp_id]:

                    tp_id = ObjectId(tp_id)
                    tp_doc = toolpaths.find_one(tp_id)
                    if tp_doc is None:
                        await self.server_transmit(sender, ("NONEXISTENT_OBJECT", str(tp_id)))
                        continue

                    wp_list = tp_doc["wps"]
                    wp_list.append(wp_id)
                    new_list = {"$set": {"wps": wp_list}}
                    result = toolpaths.update_one({"_id": tp_id}, new_list)
                    if result.acknowledged and result.modified_count == 1:
                        await self.server_transmit(sender, ("ADD_TO_TP",))
                    else:
                        await self.server_transmit(sender, ("UNEXPECTED_FAILURE",))

                case ["RM_FROM_TP", tp_id, index]:
                    tp_id = ObjectId(tp_id)
                    tp_doc = toolpaths.find_one(tp_id)
                    if tp_doc is None:
                        await self.server_transmit(sender, ("NONEXISTENT_OBJECT",))
                        continue

                    wp_list = tp_doc["wps"]
                    wp_list.pop(index)
                    new_list = {"$set": {"wps": wp_list}}
                    result = toolpaths.update_one({"_id": tp_id}, new_list)
                    if result.acknowledged and result.modified_count == 1:
                        await self.server_transmit(sender, ("RM_FROM_TP",))
                    else:
                     await self.server_transmit(sender, ("UNEXPECTED_FAILURE",))

                case _:
                    await self.server_transmit(sender, ("UNKNOWN_REQUEST",))

if __name__ == "__main__":
    opd = OpData()
