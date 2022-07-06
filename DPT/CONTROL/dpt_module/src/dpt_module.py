# Author: Robert Knobloch robert.knobloch@stud.tu-darmstadt.de   

"""
Base module for all DPT modules. The main purpose is thereby establishing
the ZeroMQ communication, receiving, creating and sending the messages.
"""

import sys
import zmq
import logging
import json
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

        self.socket.send_multipart([bytes(address, encoding="ascii"), b'', msg_bytes])
        self.sysout('send message', f"to {address}: {msg_bytes}")
    
    def receive(self, timeout=None, raw_bytes=False) -> tuple[str, object|bytes]:
        """
        Poll for messages.
        
        Parameters:
        -----------
        timeout . . . . . . Time to wait for message in ms. ¨None¨ means wait forever.
        raw_bytes . . . . . True if received message is not to be decoded.        
        
        Returns:
        --------
        full_message:  (sender, message)

        Raises:
        -------
        ReceiveTimeoutException: If no message could be received in the given time
        """
 
        event = self.socket.poll(timeout=timeout)
 
        if event == zmq.POLLIN:
            (sender_bytes, _, msg_bytes) = self.socket.recv_multipart()
            sender = str(sender_bytes, encoding='ascii')
            if raw_bytes:
                self.sysout("Received message", f"From {sender}: {msg_bytes}")
                return (sender, msg_bytes)
            
            msg_json = msg_bytes.decode('ascii')
            self.sysout("Received message", f"From {sender}: {msg_json}")
            msg_pyobj = json.loads(msg_json)
            return (sender, msg_pyobj)
        
        else:
            # If there is no response within the timeout-time
            self.sysout("timeout", 
                        'No response within the timeout-time of: '+str(timeout)+' milliseconds')

            raise ReceiveTimeoutException()

    def sysout(self, action, meta="UnspecifiedMeta") -> None:
        """Meta is limited to 200 chars at the moment
        """
        meta = str(meta)
        
        info_out = f"""\n<> FUNCTIONALITY [{str(self.name)}] #{str(action)} 
                       -> { meta[0:150]+'...' if len(meta) > 150 else meta}"""
                       
        sys.stdout.write(info_out)
        logging.info(info_out)

    def destroy(self) -> None:
        self.socket.close()
        self.context.destroy()


class ReceiveTimeoutException(Exception):
    def __init__(self,*args,**kwargs):
        Exception.__init__(self,*args,**kwargs)


class Requests(IntEnum):
    NEW_WP = 0
    GET_WP = 1
    GET_ALL_WP_IDS = 2
