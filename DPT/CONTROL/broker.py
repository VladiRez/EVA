# Author: Robert Knobloch, robert.knobloch@stud.tu-darmstadt.de
"""
The main function of the broker is to forward incoming messages to the proper receiver.
"""

import sys
import zmq
import logging
import json
from os import path, pardir

class broker():
    """Run mediate() in infinite loop to use the broker.
    Broker runs on ip: tcp://127.0.0.1:5554.
    """
    
    def __init__(self):
        logging.basicConfig(format='%(asctime)s %(message)s', level=logging.INFO)

        # Start ZeroMQ connection 
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.ROUTER)
        self.socket.bind("tcp://127.0.0.1:5554")
        
        self.sysout("started", "BROKER", f"Running on socket {str(self.socket)}")

    def mediate(self):
        """Receive and forward incoming messages.
        """
        while True:
            
            try:
                sender, address, _, msg = self.socket.recv_multipart(copy=True)
            except KeyboardInterrupt:
                break
            
            sender_str = bytes.decode(sender, encoding="ascii")
            address_str = bytes.decode(address, encoding="ascii")
            self.sysout('route message', aas_module="Broker", 
                        meta = f"From {sender_str} to {address_str}: {msg}")
            
            self.socket.send_multipart([address, sender, b'', msg])

    def sysout(self, action, aas_module="UnspecifiedModule", meta="UnspecifiedMeta"):
        """ Meta is limited to 150 characters.
        """
        
        meta = str(meta)
        info_out = f"""\n<> CONTROL [{str(aas_module)}] #{str(action)} 
                       -> { meta[0:150]+'...' if (len(meta) > 150) else meta}"""
         
        sys.stdout.write(info_out)
        logging.info(info_out)
            
        sys.stdout.flush()
    
    def destroy(self):
        self.sysout('Control closed')
        self.context.destroy()
