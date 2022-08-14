"""
author: robert.knobloch@stud.tu-darmstadt.de

Program managing the operational data storage (MongoDB) of the DPT.
PyMongo docs: https://pymongo.readthedocs.io/en/stable/
"""

from pymongo import MongoClient
from bson.objectid import ObjectId
import time
import logging
import asyncio
import os


from dpt_module import DptModule, Requests, Responses

class OpData(DptModule):
    """
    Class for interfacing with the Operational Data Storage
    """
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)

    def __init__(self):
        db_address = os.environ["DB_ADDRESS"]

        self.client = MongoClient(db_address)
        self.db = self.client["dpt_op_data"]

        super().__init__()
        asyncio.run(self.entrypoint())
        

    async def entrypoint(self):
        """ Asynchronous entrypoint to be used with asyncio.run()
        """
        task_server_loop = asyncio.create_task(self.server_loop())
        task_service_loop = asyncio.create_task(self.service_loop())

        await asyncio.gather(task_server_loop, task_service_loop)

    async def service_loop(self) -> None:
        """
        Loop for listening to incoming requests.
        Expects a tuple with the first entry being the request type.
        """

        while True:

            col_waypoints = self.db["waypoints"]
            toolpaths = self.db["toolpaths"]
            (sender, msg) = await self.server_receive()

            if msg[0] == Requests.SHUTDOWN:
                break

            if msg[0] == Requests.NEW_WP:
                post = {"coordinates": msg[1],
                        "wp_name": "New WP",
                        "creation_time": time.time()}
                hash_id = col_waypoints.insert_one(post).inserted_id

            elif msg[0] == Requests.GET_WP:
                hash_id = ObjectId(msg[1])
                wp_doc = col_waypoints.find_one(hash_id)
                if wp_doc is None:
                    await self.server_transmit(sender, (str(hash_id), Responses.NONEXISTENT_OBJECT))

                wp_coor = wp_doc["coordinates"]
                wp_name = wp_doc["wp_name"]
                wp_time = wp_doc["creation_time"]
                await self.server_transmit(sender, (str(hash_id), wp_name, wp_coor, wp_time))

            elif msg[0] == Requests.GET_ALL_WP_IDS:
                all_wps_cursor = col_waypoints.find({})
                wp_all_ids = [str(wp["_id"]) for wp in all_wps_cursor]
                all_wps_cursor = col_waypoints.find({})
                wp_all_names = [wp["wp_name"] for wp in all_wps_cursor]
                await self.server_transmit(sender, (wp_all_ids, wp_all_names))

            elif msg[0] == Requests.DEL_WP:
                hash_id = ObjectId(msg[1])
                result = col_waypoints.delete_one({"_id": hash_id})
                if result.acknowledged and result.deleted_count == 1:
                    await self.server_transmit(sender, Requests.DEL_WP)
                else:
                    await self.server_transmit(sender, Responses.UNEXPECTED_FAILURE)

            elif msg[0] == Requests.CHANGE_WP_NAME:
                hash_id = ObjectId(msg[1])
                new_value = {"$set": {"wp_name": msg[2]}}
                result = col_waypoints.update_one({"_id": hash_id}, new_value)
                if result.acknowledged and result.modified_count == 1:
                    await self.server_transmit(sender, Requests.CHANGE_WP_NAME)
                else:
                    await self.server_transmit(sender, Responses.UNEXPECTED_FAILURE)

            if msg[0] == Requests.NEW_TP:
                pass

            if msg[0] == Requests.ADD_TO_TP:
                hash_id = ObjectId(msg[1])
                tp_doc = toolpaths.find_one(hash_id)
                if tp_doc is None:
                    await self.server_transmit(sender, (str(hash_id), Responses.NONEXISTENT_OBJECT))

                wp_list = tp_doc["wps"]
                wp_list.append(msg[2])
                new_list = {"$set": {"wps": wp_list}}
                result = toolpaths.update_one({"_id": hash_id}, new_list)
                if result.acknowledged and result.modified_count == 1:
                    await self.server_transmit(sender, Requests.ADD_TO_TP)
                else:
                    await self.server_transmit(sender, Responses.UNEXPECTED_FAILURE)

            if msg[0] == Requests.RM_FROM_TP:
                hash_id = ObjectId(msg[1])
                index = msg[2]
                tp_doc = toolpaths.find_one(hash_id)
                if tp_doc is None:
                    await self.server_transmit(sender, Responses.NONEXISTENT_OBJECT)
                wp_list = tp_doc["wps"]
                wp_list.pop(index)
                new_list = {"$set": {"wps": wp_list}}
                result = toolpaths.update_one({"_id": hash_id}, new_list)
                if result.acknowledged and result.modified_count == 1:
                    await self.server_transmit(sender, Requests.RM_FROM_TP)
                else:
                    await self.server_transmit(sender, Responses.UNEXPECTED_FAILURE)

            if msg[0] == Requests.GET_TP:
                hash_id = ObjectId(msg[1])
                tp_doc = toolpaths.find_one(hash_id)
                if tp_doc is None:
                    await self.server_transmit(sender, (str(hash_id), Responses.NONEXISTENT_OBJECT))

                wp_list = tp_doc["wps"]
                await self.server_transmit(sender, (str(hash_id), wp_list))

if __name__ == "__main__":
    opd = OpData()
    opd.listen()

