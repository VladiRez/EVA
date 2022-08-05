# Author: Robert Knobloch robert.knobloch@stud.tu-darmstadt.de   

"""
Base module for all DPT modules. The main purpose is thereby establishing
the ZeroMQ communication, receiving, creating and sending the messages.
"""

import sys
import zmq.asyncio
import logging
import json
import time
import os
import asyncio
from enum import IntEnum

class DptModule():
    """Base module for all DPT modules.
    """

    def __init__(self):
        """Definition of the parameter of a module derived from this class.
        """        
        
        logging.basicConfig(format='%(asctime)s %(message)s',
                            level=logging.DEBUG)

        self.zmq_port = os.environ["ZMQ_PORT"]

        # ZeroMQ Setup        
        self.context = zmq.asyncio.Context()
        self.server_socket = self.context.socket(zmq.ROUTER)
        self.server_socket.bind(f"tcp://*:{self.zmq_port}")
        self.client_sockets = {}

        self.server_msg_queue = asyncio.Queue()

        self.sysout("started", f"Started Service")
        self.sysout("started", f"Running server_socket on {str(self.server_socket.underlying)}")

    async def register_connection(self, address: str) -> bool:
        new_socket = self.context.socket(zmq.DEALER)
        new_socket.connect(f"tcp://{address}:{self.zmq_port}")
        new_socket.send(b"confirm_connection")

        event = await new_socket.poll(timeout=100)
        if event != zmq.POLLIN:
            return False
        if await new_socket.recv() != b"connection_confirmed":
            return False

        self.sysout("Outgoing connection established", f"To {address}")
        self.client_sockets[address] = new_socket                
        return True


    async def client_transmit(self, address: str, message: object) -> None:
        """
        Transmit message to module using the broker.
        Sends messages as json.
        
        Parameters:
        -----------
        address . . . . . . Name of the module to receive the message.
        message . . . . . . Any object to be sent
        """

        msg_json = json.dumps(message)
        msg_bytes = msg_json.encode('ascii')

        try:
            client_socket = self.client_sockets[address]
        except KeyError:
            raise BaseModuleException("Module with that address not registered.")

        
        await client_socket.send(msg_bytes, flags=zmq.DONTWAIT)
        self.sysout('send message', f"to {address}: {msg_bytes}")


    async def server_transmit(self, address: bytes, message: object) -> None:
        msg_json = json.dumps(message)
        msg_bytes = msg_json.encode('ascii')
        await self.server_socket.send_multipart([address, msg_bytes])


    async def client_receive(self, address: str, timeout=None) -> object:
        try:
            client_socket = self.client_sockets[address]
        except KeyError:
            raise BaseModuleException("Module with that address not registered.")

        event = await client_socket.poll(timeout=timeout)
        if event != zmq.POLLIN:
            raise BaseModuleException(
                f"Timeout while receiving message on client socket (to f{address}).")

        msg_bytes = await client_socket.recv()
        msg_json = msg_bytes.decode('ascii')
        self.sysout("Received message", f"From {address}: {msg_json}")
        msg_pyobj = json.loads(msg_json)  
        return msg_pyobj


    async def monitor_server_socket(self) -> None:
        while True:
            (sender, msg_bytes) = await self.server_socket.recv_multipart()

            if msg_bytes == b"confirm_connection":
                await self.server_socket.send_multipart([sender, b"connection_confirmed"])
                self.sysout("Incoming connection established", f"From {sender}")
                continue

            msg_json = msg_bytes.decode('ascii')
            self.sysout("Received message", f"From {sender}: {msg_json}")
            msg_pyobj = json.loads(msg_json)   

            await self.server_msg_queue.put((sender, msg_pyobj))


    async def flush_queue(self) -> None:
        """
        Method to clear the modules message queue as to avoid reading dead messages.
        """
        try:
            for _ in self.server_msg_queue.qsize():
                self.server_msg_queue.get_nowait()
        except asyncio.QueueEmpty:
            return

    def shutdown(self) -> None:
        self.socket.close()
        self.context.term()

    def sysout(self, action, meta="UnspecifiedMeta") -> None:
        """
        Format logging text

        Meta is limited to 200 chars at the moment
        """
        meta = str(meta)
        
        info_out = f"""\n<> FUNCTIONALITY #{str(action)} 
                       -> { meta[0:150]+'...' if len(meta) > 150 else meta}"""
                       
        #sys.stdout.write(info_out)
        logging.debug(info_out)

    def destroy(self) -> None:
        self.socket.close()
        self.context.destroy()


""""
CONSTANTS
"""

class Requests(IntEnum):
    # General Requests
    SHUTDOWN = 1000

    # Database Requests
    NEW_WP = 0
    GET_WP = 1
    GET_ALL_WP_IDS = 2
    DEL_WP = 3
    CHANGE_WP_NAME = 4

    # Eva Requests
    BACKDRIVING_MODE = 10
    STOP_BACKDRIVING = 11
    GOTO_WP = 12


class Responses(IntEnum):
    # General Responses
    UNEXPECTED_FAILURE = -1
    UNKNOWN_COMMAND = -2

    # Database Responses
    NONEXISTENT_WAYPOINT = -10

    # Eva Responses
    LOCK_FAILED = -20




"""
EXCEPTIONS
"""


class BaseModuleException(Exception):
    def __init__(self,*args,**kwargs):
        Exception.__init__(self,*args,**kwargs)


