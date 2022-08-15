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
import random
from enum import IntEnum

class BaseModule():
    """Base module for all DPT modules.

    Each module consists of two parts: Server and Client.
    The server has one socket that clients (other modules) can connect to.
    A client opens one socket for each server connection.

    The module is asynchronous (using the python asyncio package),
    meaning the use case has to consider that.

    NECESSARY OS ENVIRONMENTS FOR ALL MODULES:
    ZMQ_PORT: Port on which all zmq communication should happen
    MODULE_NAME: Name for registration of client socket on the server socket

    Client Methods:
    ---------------
    register_connection:
        Create a socket and connect it to a server (dpt-module)
    client_transmit:
        Transmit a message to a specific server. Register connection first.
    client_receive:
        Wait for a message from a specific server. Register connection first.
    

    Server Methods:
    ---------------
    server_transmit:
        Transmit a message to a connected client.
    server_receive:
        Receive a message on the server socket.
    flush_server_socket:
        Drop old messages to server.

    """

    def __init__(self):   

        logging.basicConfig(format='%(asctime)s %(message)s',
                            level=logging.INFO)

        self.zmq_port = os.environ["ZMQ_PORT"]
        unique_id = hash(time.time() + random.randint(0, 1024))
        self.name = os.environ["MODULE_NAME"] + "_" + str(unique_id)
        
        # ZeroMQ Setup        
        self.context = zmq.asyncio.Context()
        self.client_sockets = {}
        self.server_socket = self.context.socket(zmq.ROUTER)
        self.server_socket.bind(f"tcp://*:{self.zmq_port}")

        self.server_msg_queue = asyncio.Queue()

        logging.info(f"Started Service")

    # CLIENT METHODS
    ##########################################################################

    def register_connection(self, address: str):
        """ Connects to a server (dpt module).

        Parameters:
        -----------
        address: Either the ip address or the DNS domain name
        """


        new_socket = self.context.socket(zmq.DEALER)
        new_socket.setsockopt(zmq.LINGER, 0)
        new_socket.setsockopt_string(zmq.IDENTITY, self.name)
        new_socket.connect(f"tcp://{address}:{self.zmq_port}")
        
        self.client_sockets[address] = new_socket 
                 
        return

    async def client_transmit(self, address: str, message: tuple) -> None:
        """Transmits message to server. 
        A connection to the server has to be already established.
        
        Parameters:
        -----------
        address: IP or DNS domain name of the server
        message: Any object to be sent

        Raises:
        -------
        BaseModuleException: If no server with given address has been
            registered.
        """

        msg_json = json.dumps(message)
        msg_bytes = msg_json.encode('ascii')

        try:
            client_socket = self.client_sockets[address]
        except KeyError:
            raise BaseModuleException("Module with that address not registered.")

        
        await client_socket.send(msg_bytes, flags=zmq.DONTWAIT)
        logging.info(f"Send message to {address}: {msg_bytes}")

    async def client_receive(self, address: str, timeout:int =None) -> tuple[object]:
        """ Receives a message from a specific server.
        A connection to the server has to be already established.

        Parameters:
        -----------
        address: IP or DNS domain name of the server
        timeout: Time to wait for message until raising an exception in ms.
            Default: None

        Raises:
        -------
        BaseModuleException: If no server with given address has been
            registered or no message was received until timeout
        
        """
        
        if not address in self.client_sockets.keys():
            raise BaseModuleException("Module with that address not registered.")

        sock = self.client_sockets[address]
        event = await sock.poll(timeout=timeout)
        if event != zmq.POLLIN:
            raise TimeoutException()

        msg_bytes = await sock.recv()
        msg_json = msg_bytes.decode('ascii')
        logging.info(f"Received message From {address}: {msg_json}")
        msg_pyobj = json.loads(msg_json)  
        return msg_pyobj


    # SERVER METHODS
    ##########################################################################

    async def server_transmit(self, address: bytes, message: tuple[object]) -> None:
        """Transmits message to connected client.

        Parameters:
        -----------
        address: zmq given address of connected client (is given in queued
            messages)
        message: Any pyobject to send
        """
        
        msg_json = json.dumps(message)
        msg_bytes = msg_json.encode('ascii')
        logging.info(f"Sending message: {message} to {address}")
        await self.server_socket.send_multipart([address, msg_bytes])


    async def server_receive(self) -> tuple[bytes, object]:
        (sender, msg_bytes) = await self.server_socket.recv_multipart()
        msg_json = msg_bytes.decode("ascii")
        logging.info(f"Received message from {sender}: {msg_json}")
        msg_pyobj = json.loads(msg_json)
        return (sender, msg_pyobj)
        

    async def flush_server_socket(self) -> None:
        """ Drop old messages
        """
        try:
            while True:
                await self.server_socket.recv(flags=zmq.DONTWAIT)
        except zmq.Again:
            return


class BaseModuleException(Exception):
    def __init__(self,*args,**kwargs):
        Exception.__init__(self,*args,**kwargs)

class TimeoutException(BaseModuleException):
    def __init__(self,*args,**kwargs):
        super().__init__(self,*args,**kwargs)

