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

class DptModule():
    """Base module for all DPT modules.

    Each module consists of two parts: Server and Client.
    The server has one socket that clients (other modules) can connect to.
    A client opens one socket for each server connection.

    The module is asynchronous (using the python asyncio package),
    meaning the use case has to consider that.
    All methods with _loop in it have to be cled manually (mytask.cancel()).

    NECESSARY OS ENVIRONMENTS FOR ALL MODULES:
    ZMQ_PORT: Port on which all zmq communication should happen

    Client Methods:
    ---------------
    register_connection:
        Create a socket and connect it to a server (dpt-module)
    client_transmit:
        Transmit a message to a specific server. Register connection first.
    client_receive:
        Wait for a message from a specific server. Register connection first.
    client_hc_loop:
        Monitors the connection status of the client sockets (health check)

    Server Methods:
    ---------------
    server_transmit:
        Transmit a message to a connected client.
    server_loop:
        Run server loop that collects msgs and confirms client connections.
    flush_queue:
        Flush message queue.

    Important Attributes:
    ---------------------
    server_msg_queue: asyncio.Queue
        server method server_loop puts received messages in this
        queue. Flush with flush_queue. Use this queue to process messages in
        app.

    client_sockets: dict{address: str, socket: zmq.Socket}
        dictionary that contains every client socket and its address as key
    """

    def __init__(self):   

        logging.basicConfig(format='%(asctime)s %(message)s',
                            level=logging.INFO)

        self.zmq_port = os.environ["ZMQ_PORT"]
        unique_id = hash(time.time() + random.randint(0, 1024))
        self.name = os.environ["MODULE_NAME"] + str(unique_id)
        
        # ZeroMQ Setup        
        self.context = zmq.asyncio.Context()
        self.client_sockets = {}
        self.client_hc_sockets = {}
        self.server_socket = self.context.socket(zmq.ROUTER)
        self.server_socket.bind(f"tcp://*:{self.zmq_port}")

        self.server_msg_queue = asyncio.Queue()
        self.server_connected_addr = []

        self.interrupted_sockets = []

        self.client_check_connections_interval = 3

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

        health_check_socket = self.context.socket(zmq.DEALER)
        health_check_socket.setsockopt(zmq.LINGER, 0)
        health_check_socket.setsockopt_string(zmq.IDENTITY, self.name+"_hc")
        health_check_socket.connect(f"tcp://{address}:{self.zmq_port}")

        self.client_hc_sockets[address] = health_check_socket
                 
        return

    async def client_transmit(self, address: str, message: object) -> None:
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

    async def client_receive(self, address: str, timeout:int =None) -> object:
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
            raise BaseModuleException(
                f"Timeout while receiving message on client socket (from {address}).")

        msg_bytes = await sock.recv()
        msg_json = msg_bytes.decode('ascii')
        logging.info(f"Received message From {address}: {msg_json}")
        msg_pyobj = json.loads(msg_json)  
        return msg_pyobj

    async def client_hc_loop(self) -> None:
        """ Monitors the connection status of the client sockets (health check)
        """
        while True:
            await asyncio.sleep(self.client_check_connections_interval)
            for (address, hc_socket) in self.client_hc_sockets.items():
                await hc_socket.send(b"check_connection", flags=zmq.DONTWAIT)
                event = await hc_socket.poll(timeout=100)
                if event == zmq.POLLIN:
                    msg = await hc_socket.recv()
                    if address in self.interrupted_sockets and msg == b"connection_alive":
                        logging.info(f"Connection reestablished to {address}")
                        self.interrupted_sockets.remove(address)
                    continue
                
                # Health check negative:
                logging.info(f"No connection to {address}")
                if address not in self.interrupted_sockets:
                    self.interrupted_sockets.append(address)
                    continue


    # SERVER METHODS
    ##########################################################################

    async def server_loop(self) -> None:
        """ Creates loop to receive messages and puts these messages in the
        self.server_msg_queue Queue.
        Confirms client connections automatically.

        Run this as an asyncio task in the app
        """
        await self.flush_server_socket()
        while True:
            (sender, msg_bytes) = await self.server_socket.recv_multipart()

            if msg_bytes == b"check_connection":
                await self.server_socket.send_multipart([sender, b"connection_alive"])
                if sender not in self.server_connected_addr:
                    self.server_connected_addr.append(sender)
                    logging.info(f"Incoming connection established from {sender}")
                continue

            msg_json = msg_bytes.decode('ascii')
            logging.info(f"Received message From {sender}: {msg_json}")
            msg_pyobj = json.loads(msg_json)   

            await self.server_msg_queue.put((sender, msg_pyobj))

    async def server_transmit(self, address: bytes, message: object) -> None:
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
        return await self.server_msg_queue.get()
        

    def flush_server_queue(self) -> None:
        """
        Method to clear the modules message queue as to avoid reading dead messages.
        """
        try:
            for _ in self.server_msg_queue.qsize():
                self.server_msg_queue.get_nowait()
        except asyncio.QueueEmpty:
            return

    async def flush_server_socket(self) -> None:
        try:
            while True:
                await self.server_socket.recv(flags=zmq.DONTWAIT)
        except zmq.Again:
            return


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
    NEW_TP = 5
    ADD_TO_TP = 6
    GET_TP = 7
    RM_FROM_TP = 8

    # Eva Requests
    BACKDRIVING_MODE = 10
    STOP_BACKDRIVING = 11
    GOTO_WP = 12
    EXECUTE_TP = 13


class Responses(IntEnum):
    # General Responses
    UNEXPECTED_FAILURE = -1
    UNKNOWN_COMMAND = -2

    # Database Responses
    NONEXISTENT_OBJECT = -10

    # Eva Responses
    LOCK_FAILED = -20




"""
EXCEPTIONS
"""


class BaseModuleException(Exception):
    def __init__(self,*args,**kwargs):
        Exception.__init__(self,*args,**kwargs)


