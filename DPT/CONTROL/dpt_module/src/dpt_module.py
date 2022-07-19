# Author: Robert Knobloch robert.knobloch@stud.tu-darmstadt.de   

"""
Base module for all DPT modules. The main purpose is thereby establishing
the ZeroMQ communication, receiving, creating and sending the messages.
"""

import sys
import zmq
import logging
import json
import time
from enum import IntEnum

class DptModule():
    """Base module for all DPT modules.
    """

    def __init__(self, module_name):
        """Definition of the parameter of a module derived from this class.
        """        
        
        logging.basicConfig(format='%(asctime)s %(message)s',
                            level=logging.DEBUG)
       
        # ZeroMQ Setup        
        self.context = zmq.Context()
        self.name = module_name
        self.socket = self.context.socket(zmq.DEALER)
        self.socket.setsockopt_string(zmq.IDENTITY, self.name)
        self.socket.setsockopt(zmq.LINGER, 0)
        self.socket.connect(f"tcp://127.0.0.1:5554")
        self.sysout("started", f"Running on socket {str(self.socket)}")

    def transmit(self, address: str, message: object) -> None:
        """
        Transmit message to module using the broker.
        Sends messages as json, except if message is a bytes object.
        
        Parameters:
        -----------
        address . . . . . . Name of the module to receive the message.
        message . . . . . . Any object to be sent
        """
        
        if isinstance(message, bytes):
            msg_bytes = message
        else: 
            msg_json = json.dumps(message)
            msg_bytes = msg_json.encode('ascii')

        self.socket.send_multipart([bytes(address, encoding="ascii"), b'', msg_bytes],
                                   flags=zmq.DONTWAIT)
        self.sysout('send message', f"to {address}: {msg_bytes}")
    
    def receive(self, from_sender: str = None, expected_msg: tuple[object] = None,
                timeout=None, raw_bytes=False) -> tuple[str, object | bytes]:
        """
        Poll for messages.
        
        Parameters:
        -----------
        from_sender . . . . Only accept messages from this sender
        expected_msg  . . . Only accept messages with this content
        timeout . . . . . . Time to wait for message in ms. ¨None¨ means wait forever.
        raw_bytes . . . . . True if received message is not to be decoded.        
        
        Returns:
        --------
        full_message:  (sender, message)

        Raises:
        -------
        ReceiveTimeoutException: If no message could be received in the given time
        """

        t0 = time.perf_counter()
        # The time since the start of the method
        # This is being used to determined if timeout is reached in case that messages came in
        # but not from the desired sender.
        delta_t = 0

        # If from_sender is set: Loop until message arrives from correct sender or timeout
        # is reached
        while True:
            if timeout is not None:
                # If from_sender is set: Decrease timeout by time passed since method start
                timeout = timeout - delta_t
            event = self.socket.poll(timeout=timeout)

            # Updating the passed time
            t1 = time.perf_counter()
            delta_t = t1 - t0

            if event == zmq.POLLIN:
                (sender_bytes, _, msg_bytes) = self.socket.recv_multipart()
                sender = str(sender_bytes, encoding='ascii')

                # Only regard messages from desired sender
                if from_sender is not None and sender != from_sender:
                    continue

                # If the message should not be unpacked
                if raw_bytes:
                    self.sysout("Received message", f"From {sender}: {msg_bytes}")

                    # Continue if message is not the one expected
                    if expected_msg is not None and msg_bytes not in expected_msg:
                        continue

                    return (sender, msg_bytes)

                msg_json = msg_bytes.decode('ascii')
                self.sysout("Received message", f"From {sender}: {msg_json}")
                msg_pyobj = json.loads(msg_json)

                # Continue if message is not one of the expected ones
                if expected_msg is not None and msg_pyobj not in expected_msg:
                    continue

                return (sender, msg_pyobj)

            else:
                # If there is no response within the timeout-time
                self.sysout("timeout",
                            'No response within the timeout-time of: '+str(timeout)+' milliseconds')

                raise ReceiveTimeoutException()

        # Raise Timeout if no message from desired sender was received in time
        raise ReceiveTimeoutException()

    def flush_queue(self) -> None:
        """
        Method to clear the modules message queue as to avoid reading dead messages.
        """
        try:
            for i in range(1000):
                self.socket.recv_multipart(zmq.DONTWAIT)
        except zmq.error.Again:
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
        
        info_out = f"""\n<> FUNCTIONALITY [{str(self.name)}] #{str(action)} 
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

    # Eva Requests
    BACKDRIVING_MODE = 10
    STOP_BACKDRIVING = 11


class Responses(IntEnum):
    # Database Responses
    NONEXISTENT_WAYPOINT = -1

    # Eva Responses
    LOCK_FAILED = -2




"""
EXCEPTIONS
"""


class ReceiveTimeoutException(Exception):
    def __init__(self,*args,**kwargs):
        Exception.__init__(self,*args,**kwargs)


