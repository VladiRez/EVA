"""
author: robert.knobloch@stud.tu-darmstadt.de

Program managing the operational data storage (MongoDB) of the DPT.
PyMongo docs: https://pymongo.readthedocs.io/en/stable/
"""

from pymongo import MongoClient
from bson.objectid import ObjectId
from bson.json_util import dumps
import time
import logging
import os
import json


from base_module import BaseModule

logging.basicConfig(level=logging.DEBUG)

class OpData(BaseModule):
    """
    Class for interfacing with the Operational Data Storage

    Necessary OS Environment Variables:
    -----------------------------------
    DB_ADDRESS: ip or domain dame of the mongodb database

    Service requests:
    -----------------
    SHUTDOWN, NEW_WP, GET_WP, GET_ALL_WP_IDS, CHANGE_WP_NAME,
    NEW_TP, GET_TP, ADD_TO_TP, RM_FROM_TP 
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

        col_waypoints = self.db["waypoints"]
        col_toolpaths = self.db["toolpaths"]

        while True:
            
            (sender, req_id, msg) = await self.server_receive()
            resp_id = req_id

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
                        await self.server_transmit(sender, resp_id, ("NONEXISTENT_OBJECT", str(wp_id)))
                        continue

                    wp_coor = wp_doc["coordinates"]
                    wp_name = wp_doc["wp_name"]
                    wp_time = wp_doc["creation_time"]
                    await self.server_transmit(sender, resp_id, 
                        ("GET_WP", str(wp_id), wp_name, wp_coor, wp_time))
                
                case ["GET_ALL_WP_IDS"]:
                    all_wps_cursor = col_waypoints.find({})
                    wp_all_ids = [str(wp["_id"]) for wp in all_wps_cursor]
                    all_wps_cursor = col_waypoints.find({})
                    wp_all_names = [wp["wp_name"] for wp in all_wps_cursor]
                    await self.server_transmit(sender, resp_id, ("GET_ALL_WP_IDS", wp_all_ids, wp_all_names))

                case ["DEL_WP", wp_id]:
                    wp_id = ObjectId(wp_id)
                    result = col_waypoints.delete_one({"_id": wp_id})
                    if result.acknowledged and result.deleted_count == 1:
                        await self.server_transmit(sender, resp_id, ("DEL_WP",))
                    else:
                        await self.server_transmit(sender, resp_id, ("UNEXPECTED_FAILURE",))

                case ["CHANGE_WP_NAME", wp_id, wp_name]:
                    wp_id = ObjectId(wp_id)
                    new_value = {"$set": {"wp_name": wp_name}}
                    result = col_waypoints.update_one({"_id": wp_id}, new_value)
                    if result.acknowledged and result.modified_count == 1:
                        await self.server_transmit(sender, resp_id, ("CHANGE_WP_NAME",))
                    else:
                        await self.server_transmit(sender, resp_id, ("UNEXPECTED_FAILURE",))

                case ["NEW_TP"]:
                    post = {"tp_name": "New TP",
                            "creation_time": time.time(),
                            "timeline": []}
                    tp_id = col_toolpaths.insert_one(post).inserted_id
                    await self.server_transmit(sender, resp_id, ("NEW_TP", str(tp_id)))

                case ["GET_TP", tp_id]:
                    tp_id = ObjectId(tp_id)
                    tp_doc = col_toolpaths.find_one(tp_id)
                    if tp_doc is None:
                        await self.server_transmit(sender, resp_id, ("NONEXISTENT_OBJECT", str(tp_id)))
                        continue

                    timeline = tp_doc["timeline"]
                    tp_name = tp_doc["tp_name"]
                    await self.server_transmit(sender, resp_id, ("GET_TP", str(tp_id), tp_name,
                                                                 timeline))

                case ["DEL_TP", wp_id]:
                    tp_id = ObjectId(tp_id)
                    result = col_toolpaths.delete_one({"_id": tp_id})
                    if result.acknowledged and result.deleted_count == 1:
                        await self.server_transmit(sender, resp_id, ("DEL_TP",))
                    else:
                        await self.server_transmit(sender, resp_id, ("UNEXPECTED_FAILURE",))

                case ["GET_ALL_TP_IDS"]:
                    all_tps_cursor = col_toolpaths.find({})
                    tp_all_ids = [str(tp["_id"]) for tp in all_tps_cursor]
                    all_tps_cursor = col_toolpaths.find({})
                    tp_all_names = [tp["tp_name"] for tp in all_tps_cursor]
                    await self.server_transmit(sender, resp_id,
                                               ("GET_ALL_TP_IDS", tp_all_ids, tp_all_names))

                case ["CHANGE_TP_NAME", tp_id, new_name]:
                    tp_id = ObjectId(tp_id)
                    new_value = {"$set": {"tp_name": new_name}}
                    result = col_toolpaths.update_one({"_id": tp_id}, new_value)
                    if result.acknowledged and result.modified_count == 1:
                        await self.server_transmit(sender, resp_id, ("CHANGE_TP_NAME",))
                    else:
                        await self.server_transmit(sender, resp_id, ("UNEXPECTED_FAILURE",))

                case ["ADD_WP_TO_TP", tp_id, wp_id]:

                    tp_id = ObjectId(tp_id)
                    tp_doc = col_toolpaths.find_one(tp_id)
                    if tp_doc is None:
                        await self.server_transmit(sender, resp_id,
                                                   ("NONEXISTENT_OBJECT", str(tp_id)))
                        continue

                    timeline = tp_doc["timeline"]
                    timeline.append(wp_id)
                    new_list = {"$set": {"timeline": timeline}}
                    result = col_toolpaths.update_one({"_id": tp_id}, new_list)
                    if result.acknowledged and result.modified_count == 1:
                        await self.server_transmit(sender, resp_id, ("ADD_WP_TO_TP",))
                    else:
                        await self.server_transmit(sender, resp_id, ("UNEXPECTED_FAILURE",))

                case ["ADD_GRIP_TO_TP", tp_id]:
                    tp_id = ObjectId(tp_id)
                    tp_doc = col_toolpaths.find_one(tp_id)
                    if tp_doc is None:
                        await self.server_transmit(sender, resp_id,
                                                   ("NONEXISTENT_OBJECT", str(tp_id)))
                        continue

                    timeline = tp_doc["timeline"]
                    timeline.append("GRIP")
                    new_list = {"$set": {"timeline": timeline}}
                    result = col_toolpaths.update_one({"_id": tp_id}, new_list)
                    if result.acknowledged and result.modified_count == 1:
                        await self.server_transmit(sender, resp_id, ("ADD_GRIP_TO_TP",))
                    else:
                        await self.server_transmit(sender, resp_id, ("UNEXPECTED_FAILURE",))

                case ["ADD_UNGRIP_TO_TP", tp_id]:
                    tp_id = ObjectId(tp_id)
                    tp_doc = col_toolpaths.find_one(tp_id)
                    if tp_doc is None:
                        await self.server_transmit(sender, resp_id,
                                                   ("NONEXISTENT_OBJECT", str(tp_id)))
                        continue

                    timeline = tp_doc["timeline"]
                    timeline.append("UNGRIP")
                    new_list = {"$set": {"timeline": timeline}}
                    result = col_toolpaths.update_one({"_id": tp_id}, new_list)
                    if result.acknowledged and result.modified_count == 1:
                        await self.server_transmit(sender, resp_id, ("ADD_UNGRIP_TO_TP",))
                    else:
                        await self.server_transmit(sender, resp_id, ("UNEXPECTED_FAILURE",))

                case ["TP_MOVE_ACTION_TO_POS", tp_id, from_pos, to_pos]:
                    tp_id = ObjectId(tp_id)
                    tp_doc = col_toolpaths.find_one(tp_id)
                    if tp_doc is None:
                        await self.server_transmit(sender, resp_id, ("NONEXISTENT_OBJECT",))
                        continue

                    timeline = tp_doc["timeline"]
                    element = timeline.pop(from_pos)
                    timeline.insert(to_pos, element)
                    new_list = {"$set": {"timeline": timeline}}
                    result = col_toolpaths.update_one({"_id": tp_id}, new_list)
                    if result.acknowledged and result.modified_count == 1:
                        await self.server_transmit(sender, resp_id, ("TP_MOVE_ACTION_TO_POS",))
                    else:
                        await self.server_transmit(sender, resp_id, ("UNEXPECTED_FAILURE",))

                case ["RM_FROM_TP", tp_id, index]:
                    tp_id = ObjectId(tp_id)
                    tp_doc = col_toolpaths.find_one(tp_id)
                    if tp_doc is None:
                        await self.server_transmit(sender, resp_id, ("NONEXISTENT_OBJECT",))
                        continue

                    timeline = tp_doc["timeline"]
                    timeline.pop(index)
                    new_list = {"$set": {"timeline": timeline}}
                    result = col_toolpaths.update_one({"_id": tp_id}, new_list)
                    if result.acknowledged and result.modified_count == 1:
                        await self.server_transmit(sender, resp_id, ("RM_FROM_TP",))
                    else:
                     await self.server_transmit(sender, resp_id, ("UNEXPECTED_FAILURE",))
                                    
                case _:
                    await self.server_transmit(sender, resp_id, ("UNKNOWN_REQUEST",))


if __name__ == "__main__":
    opd = OpData()
